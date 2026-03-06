package bot

import "testing"

func TestAllCommandSpecsHaveDescriptions(t *testing.T) {
	registry, err := NewRegistry(buildCommandSpecs(Dependencies{}))
	if err != nil {
		t.Fatalf("new registry: %v", err)
	}
	specs := registry.Specs()

	for _, spec := range specs {
		if spec.Name == "" {
			t.Fatalf("command spec has empty name")
		}
		if spec.Description == "" {
			t.Fatalf("command %q has empty description", spec.Name)
		}
	}
}
