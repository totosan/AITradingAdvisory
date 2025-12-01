import * as React from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Alert, AlertDescription } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { settingsClient } from "@/services/settings";
import type { ExchangeConfigStatus, ExchangeCredentials } from "@/types/settings";

interface ExchangeSettingsProps {
  onSaved?: () => void;
}

export function ExchangeSettings({ onSaved }: ExchangeSettingsProps) {
  const [status, setStatus] = React.useState<ExchangeConfigStatus | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [showForm, setShowForm] = React.useState(false);
  
  // Form state
  const [apiKey, setApiKey] = React.useState("");
  const [apiSecret, setApiSecret] = React.useState("");
  const [passphrase, setPassphrase] = React.useState("");

  // Load current status
  React.useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await settingsClient.getExchangeStatus();
      setStatus(data);
      setShowForm(!data.configured);
    } catch (err) {
      setError("Failed to load exchange status");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!apiKey || !apiSecret || !passphrase) {
      setError("All fields are required");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      const credentials: ExchangeCredentials = {
        api_key: apiKey,
        api_secret: apiSecret,
        passphrase,
      };
      
      const result = await settingsClient.saveExchangeCredentials(credentials);
      
      if (result.status === "success") {
        setSuccess("Credentials saved successfully!");
        // Clear form
        setApiKey("");
        setApiSecret("");
        setPassphrase("");
        // Reload status
        await loadStatus();
        onSaved?.();
      } else if (result.status === "warning") {
        setSuccess(`Credentials saved. ${result.validation?.message || "Validation pending."}`);
        await loadStatus();
        onSaved?.();
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError("Failed to save credentials");
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete the exchange credentials?")) {
      return;
    }
    
    try {
      setDeleting(true);
      setError(null);
      setSuccess(null);
      
      await settingsClient.deleteExchangeCredentials();
      setSuccess("Credentials deleted");
      await loadStatus();
      setShowForm(true);
    } catch (err) {
      setError("Failed to delete credentials");
      console.error(err);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium">Bitget Exchange</h3>
          <p className="text-sm text-muted-foreground">
            API credentials for real-time market data
          </p>
        </div>
        {status?.configured && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-green-500 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              Connected
            </span>
          </div>
        )}
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

      {status?.configured && !showForm && (
        <div className="rounded-lg border border-border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">API Key</span>
            <span className="text-sm font-mono">{status.api_key_masked}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Provider</span>
            <span className="text-sm capitalize">{status.provider}</span>
          </div>
          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowForm(true)}
            >
              Update Credentials
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? <Spinner className="h-4 w-4" /> : "Delete"}
            </Button>
          </div>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSave} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="apiKey">API Key</Label>
            <Input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter Bitget API key"
              autoComplete="off"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="apiSecret">API Secret</Label>
            <Input
              id="apiSecret"
              type="password"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              placeholder="Enter Bitget API secret"
              autoComplete="off"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="passphrase">Passphrase</Label>
            <Input
              id="passphrase"
              type="password"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              placeholder="Enter Bitget passphrase"
              autoComplete="off"
            />
          </div>
          
          <div className="flex gap-2">
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner className="h-4 w-4 mr-2" /> : null}
              Save Credentials
            </Button>
            {status?.configured && (
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </Button>
            )}
          </div>
        </form>
      )}

      <p className="text-xs text-muted-foreground">
        Credentials are encrypted using AES-256 encryption and stored securely.
      </p>
    </div>
  );
}
