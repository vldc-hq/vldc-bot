package bot

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"slices"
	"sort"
	"strings"
	"time"

	tgbot "github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

type Runtime struct {
	bot       *tgbot.Bot
	logger    *slog.Logger
	gw        TelegramGateway
	scheduler Scheduler
	registry  *Registry
	deps      Dependencies
}

func New(token string, httpTimeout time.Duration, logger *slog.Logger, deps Dependencies) (*Runtime, error) {
	client := &http.Client{}
	var runtimeRef *Runtime

	if httpTimeout <= 0 {
		httpTimeout = 30 * time.Second
	}

	b, err := tgbot.New(token,
		tgbot.WithHTTPClient(httpTimeout, client),
		tgbot.WithSkipGetMe(),
		tgbot.WithMiddlewares(recoveryMiddleware(logger)),
		tgbot.WithDefaultHandler(func(ctx context.Context, b *tgbot.Bot, update *models.Update) {
			if runtimeRef != nil {
				runtimeRef.routeDefault(ctx, b, update)
			}
		}),
		tgbot.WithErrorsHandler(func(err error) {
			logger.Error("telegram handler error", "error", err)
		}),
	)
	if err != nil {
		return nil, fmt.Errorf("create telegram bot: %w", err)
	}

	r := &Runtime{bot: b, logger: logger, gw: newGateway(b), scheduler: NewLocalScheduler(), deps: deps}
	runtimeRef = r

	registry, err := NewRegistry(buildCommandSpecs(deps), RequireAdminMiddleware(r.isAdmin))
	if err != nil {
		return nil, fmt.Errorf("build command registry: %w", err)
	}
	r.registry = registry
	r.registerHandlers()

	return r, nil
}

func (r *Runtime) Start(ctx context.Context) {
	r.syncCommands(ctx)
	r.startAOCPolling()
	r.startChatModeScheduler()
	r.startTowelCleanupScheduler()

	r.logger.Info("telegram bot polling started")
	r.bot.Start(ctx)
	r.logger.Info("telegram bot polling stopped")
}

func (r *Runtime) registerHandlers() {
	r.bot.RegisterHandler(tgbot.HandlerTypeMessageText, "", tgbot.MatchTypePrefix, r.routeMessage)
}

func (r *Runtime) routeMessage(ctx context.Context, _ *tgbot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}

	parsed := parseIncomingUpdate(update)
	if parsed.Command == "" {
		r.handleNonTextPolicies(ctx, parsed)
		r.handlePassiveText(ctx, parsed)
		return
	}

	h, ok := r.registry.Handler(parsed.Command)
	if !ok {
		r.logger.Debug("command is not registered", "command", parsed.Command)
		return
	}

	if err := h(ctx, parsed, r.gw); err != nil {
		r.logger.Error("command handler failed", "command", parsed.Command, "error", err)
		return
	}

	if parsed.Command == "buktopuha" {
		r.scheduleBuktopuhaRound(parsed.ChatID)
	}
}

func (r *Runtime) handlePassiveText(ctx context.Context, in IncomingUpdate) {
	if r.deps.BuktopuhaGame != nil && in.Text != "" {
		if guessed, word, score := r.deps.BuktopuhaGame.Guess(in.ChatID, in.Text); guessed {
			r.cancelBuktopuhaRound(in.ChatID)
			if err := r.bumpBuktopuhaStats(ctx, in, score); err != nil {
				r.logger.Warn("failed to bump buktopuha stats", "error", err)
			}
			_ = r.gw.SendMessage(ctx, in.ChatID, fmt.Sprintf("correct! word was %s, score=%d", word, score))
		}
	}

	if r.deps.Modes != nil && r.deps.Modes.SmileOn(in.ChatID) {
		if !in.HasSticker && !in.HasAnimation && in.MessageID != 0 {
			if err := r.gw.DeleteMessage(ctx, in.ChatID, in.MessageID); err != nil {
				r.logger.Warn("failed to enforce smile mode", "chat_id", in.ChatID, "message_id", in.MessageID, "error", err)
			}
		}
	}

	if r.deps.PrismWords == nil {
		return
	}
	if in.Text == "" || strings.HasPrefix(in.Text, "/") {
		return
	}

	words := strings.Fields(in.Text)
	now := time.Now()
	for _, word := range words {
		word = strings.ToLower(strings.TrimSpace(word))
		if word == "" || strings.HasPrefix(word, "/") {
			continue
		}
		if err := r.deps.PrismWords.Increment(ctx, word, now); err != nil {
			r.logger.Warn("failed to increment prism word", "word", word, "error", err)
		}
	}
}

func (r *Runtime) isAdmin(ctx context.Context, in IncomingUpdate) (bool, error) {
	if in.ChatID == 0 || in.UserID == 0 {
		return false, nil
	}

	member, err := r.bot.GetChatMember(ctx, &tgbot.GetChatMemberParams{ChatID: in.ChatID, UserID: in.UserID})
	if err != nil {
		return false, err
	}

	return slices.Contains([]models.ChatMemberType{models.ChatMemberTypeOwner, models.ChatMemberTypeAdministrator}, member.Type), nil
}

func parseIncomingUpdate(update *models.Update) IncomingUpdate {
	res := IncomingUpdate{}
	if update == nil || update.Message == nil {
		return res
	}

	res.ChatID = update.Message.Chat.ID
	res.MessageID = update.Message.ID
	res.Text = update.Message.Text
	if update.Message.From != nil {
		res.UserID = update.Message.From.ID
		res.Username = update.Message.From.Username
		res.FirstName = update.Message.From.FirstName
		res.LastName = update.Message.From.LastName
	}
	if update.Message.ReplyToMessage != nil {
		res.ReplyToMsgID = update.Message.ReplyToMessage.ID
		if update.Message.ReplyToMessage.From != nil {
			res.ReplyToID = update.Message.ReplyToMessage.From.ID
		}
	}
	res.HasSticker = update.Message.Sticker != nil
	res.HasAnimation = update.Message.Animation != nil
	res.HasVoice = update.Message.Voice != nil
	res.HasVideoNote = update.Message.VideoNote != nil
	if len(update.Message.NewChatMembers) > 0 {
		res.NewMembers = make([]int64, 0, len(update.Message.NewChatMembers))
		for _, m := range update.Message.NewChatMembers {
			res.NewMembers = append(res.NewMembers, m.ID)
		}
	}

	parts := strings.Fields(res.Text)
	if len(parts) > 0 && strings.HasPrefix(parts[0], "/") {
		command := strings.TrimPrefix(parts[0], "/")
		command = strings.SplitN(command, "@", 2)[0]
		res.Command = strings.ToLower(command)
		if len(parts) > 1 {
			res.Args = parts[1:]
		}
	}

	return res
}

func (r *Runtime) syncCommands(ctx context.Context) {
	specs := r.registry.Specs()
	sort.Slice(specs, func(i, j int) bool { return specs[i].Name < specs[j].Name })

	cmds := make([]models.BotCommand, 0, len(specs))
	for _, spec := range specs {
		cmds = append(cmds, models.BotCommand{Command: spec.Name, Description: spec.Description})
	}

	callCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	if _, err := r.bot.SetMyCommands(callCtx, &tgbot.SetMyCommandsParams{Commands: cmds}); err != nil {
		r.logger.Warn("set my commands failed", "error", err)
	}
}
