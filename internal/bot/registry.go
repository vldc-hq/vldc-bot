package bot

import "fmt"

type CommandSpec struct {
	Name         string
	Description  string
	Handler      CommandHandler
	RequireAdmin bool
}

type Registry struct {
	commands map[string]CommandHandler
	specs    map[string]CommandSpec
}

func NewRegistry(specs []CommandSpec, middleware ...Middleware) (*Registry, error) {
	commands := make(map[string]CommandHandler, len(specs))
	specMap := make(map[string]CommandSpec, len(specs))

	for _, spec := range specs {
		if spec.Name == "" {
			return nil, fmt.Errorf("command name must not be empty")
		}
		if spec.Handler == nil {
			return nil, fmt.Errorf("command %q handler must not be nil", spec.Name)
		}

		h := spec.Handler
		for i := len(middleware) - 1; i >= 0; i-- {
			h = middleware[i](h, spec)
		}

		commands[spec.Name] = h
		if spec.Description == "" {
			spec.Description = spec.Name
		}
		specMap[spec.Name] = spec
	}

	return &Registry{commands: commands, specs: specMap}, nil
}

func (r *Registry) Handler(name string) (CommandHandler, bool) {
	h, ok := r.commands[name]
	return h, ok
}

func (r *Registry) Names() []string {
	names := make([]string, 0, len(r.commands))
	for name := range r.commands {
		names = append(names, name)
	}

	return names
}

func (r *Registry) Specs() []CommandSpec {
	out := make([]CommandSpec, 0, len(r.specs))
	for _, spec := range r.specs {
		out = append(out, spec)
	}
	return out
}
