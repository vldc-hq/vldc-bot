package ai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const openaiBaseURL = "https://api.openai.com/v1/chat/completions"

type openaiRequest struct {
	Model    string          `json:"model"`
	Messages []openaiMessage `json:"messages"`
}

type openaiMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type openaiResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

// OpenAIGenerate calls the OpenAI chat completions API.
func OpenAIGenerate(ctx context.Context, apiKey, model, systemPrompt string) (string, error) {
	messages := []openaiMessage{
		{Role: "system", Content: systemPrompt},
	}

	reqBody := openaiRequest{
		Model:    model,
		Messages: messages,
	}

	body, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, openaiBaseURL, bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("openai request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read response: %w", err)
	}

	var oResp openaiResponse
	if err := json.Unmarshal(respBody, &oResp); err != nil {
		return "", fmt.Errorf("unmarshal response: %w", err)
	}

	if oResp.Error != nil {
		return "", fmt.Errorf("openai error: %s", oResp.Error.Message)
	}

	if len(oResp.Choices) == 0 {
		return "", fmt.Errorf("empty response from openai")
	}

	return oResp.Choices[0].Message.Content, nil
}
