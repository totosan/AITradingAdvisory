import * as React from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Alert, AlertDescription } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { settingsClient } from "@/services/settings";
import type { LLMStatus, LLMConfig } from "@/types/settings";

interface LLMSettingsProps {
  onSaved?: () => void;
}

export function LLMSettings({ onSaved }: LLMSettingsProps) {
  const [status, setStatus] = React.useState<LLMStatus | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [showForm, setShowForm] = React.useState(false);
  
  // Form state
  const [provider, setProvider] = React.useState<'ollama' | 'azure'>('azure');
  const [model, setModel] = React.useState("");
  const [baseUrl, setBaseUrl] = React.useState("http://localhost:11434");
  const [apiKey, setApiKey] = React.useState("");
  const [endpoint, setEndpoint] = React.useState("");

  // Load current status
  React.useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await settingsClient.getLLMStatus();
      setStatus(data);
      // Pre-fill form with current values
      setProvider(data.provider as 'ollama' | 'azure');
      setModel(data.model || "");
    } catch (err) {
      setError("Failed to load LLM status");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate based on provider
    if (provider === 'azure') {
      if (!endpoint || !apiKey || !model) {
        setError("Azure OpenAI requires endpoint, API key, and deployment name");
        return;
      }
    } else if (provider === 'ollama') {
      if (!model) {
        setError("Please specify a model name");
        return;
      }
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      const config: LLMConfig = {
        provider,
        model,
        ...(provider === 'ollama' ? { base_url: baseUrl } : {}),
        ...(provider === 'azure' ? { api_key: apiKey, endpoint } : {}),
      };
      
      const result = await settingsClient.saveLLMConfig(config);
      
      if (result.status === "success") {
        setSuccess("LLM configuration saved!");
        // Clear sensitive fields
        setApiKey("");
        // Reload status
        await loadStatus();
        setShowForm(false);
        onSaved?.();
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError("Failed to save LLM configuration");
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  const isAzureConfigured = status?.azure_configured;
  const currentProvider = status?.provider || 'none';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium">LLM Provider</h3>
          <p className="text-sm text-muted-foreground">
            Configure AI model for chat and analysis
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${
              isAzureConfigured || currentProvider === 'ollama' 
                ? 'bg-green-500' 
                : 'bg-yellow-500'
            }`} />
            {currentProvider === 'azure' ? 'Azure OpenAI' : 
             currentProvider === 'ollama' ? 'Ollama' : 'Not configured'}
          </span>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert variant="success">
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {!showForm && (
        <div className="rounded-lg border border-border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Provider</span>
            <span className="text-sm capitalize">{currentProvider}</span>
          </div>
          {status?.model && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Model</span>
              <span className="text-sm font-mono">{status.model}</span>
            </div>
          )}
          {status?.endpoint_masked && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Endpoint</span>
              <span className="text-sm font-mono">{status.endpoint_masked}</span>
            </div>
          )}
          {isAzureConfigured !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Azure API Key</span>
              <span className="text-sm">
                {isAzureConfigured ? '✓ Configured' : '✗ Not set'}
              </span>
            </div>
          )}
          <div className="pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowForm(true)}
            >
              Update Configuration
            </Button>
          </div>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSave} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="provider">Provider</Label>
            <Select
              id="provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value as 'ollama' | 'azure')}
            >
              <option value="azure">Azure OpenAI</option>
              <option value="ollama">Ollama (Local)</option>
            </Select>
          </div>
          
          {provider === 'azure' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="endpoint">Azure Endpoint</Label>
                <Input
                  id="endpoint"
                  type="url"
                  value={endpoint}
                  onChange={(e) => setEndpoint(e.target.value)}
                  placeholder="https://your-resource.openai.azure.com"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="azureApiKey">API Key</Label>
                <Input
                  id="azureApiKey"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter Azure OpenAI API key"
                  autoComplete="off"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="deployment">Deployment Name</Label>
                <Input
                  id="deployment"
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="e.g., gpt-4o"
                />
              </div>
            </>
          )}

          {provider === 'ollama' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="baseUrl">Ollama URL</Label>
                <Input
                  id="baseUrl"
                  type="url"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="http://localhost:11434"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="ollamaModel">Model Name</Label>
                <Input
                  id="ollamaModel"
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="e.g., llama3.2, mistral, codestral"
                />
              </div>
            </>
          )}
          
          <div className="flex gap-2">
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner className="h-4 w-4 mr-2" /> : null}
              Save Configuration
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}

      <p className="text-xs text-muted-foreground">
        API keys are encrypted with AES-256 encryption. Azure OpenAI credentials from .env are used as defaults.
      </p>
    </div>
  );
}
