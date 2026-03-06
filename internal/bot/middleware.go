package bot

import (
	"context"
	"fmt"
)

type Middleware func(next CommandHandler, spec CommandSpec) CommandHandler

type AdminChecker func(ctx context.Context, in IncomingUpdate) (bool, error)

func RequireAdminMiddleware(checker AdminChecker) Middleware {
	return func(next CommandHandler, spec CommandSpec) CommandHandler {
		if !spec.RequireAdmin {
			return next
		}

		return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
			if checker == nil {
				return fmt.Errorf("admin checker is not configured")
			}

			isAdmin, err := checker(ctx, in)
			if err != nil {
				return fmt.Errorf("check admin permission: %w", err)
			}
			if !isAdmin {
				return nil
			}

			return next(ctx, in, tg)
		}
	}
}
