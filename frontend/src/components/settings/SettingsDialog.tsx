import * as React from "react";
import { Button } from "@/components/ui/Button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/Dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { ExchangeSettings } from "./ExchangeSettings";
import { LLMSettings } from "./LLMSettings";

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [activeTab, setActiveTab] = React.useState("exchange");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>⚙️</span>
            Settings
          </DialogTitle>
          <DialogDescription>
            Configure API credentials and LLM provider settings
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="exchange">
              <span className="mr-2">📈</span>
              Exchange
            </TabsTrigger>
            <TabsTrigger value="llm">
              <span className="mr-2">🤖</span>
              LLM Provider
            </TabsTrigger>
          </TabsList>

          <TabsContent value="exchange" className="mt-4">
            <ExchangeSettings onSaved={() => {}} />
          </TabsContent>

          <TabsContent value="llm" className="mt-4">
            <LLMSettings onSaved={() => {}} />
          </TabsContent>
        </Tabs>

        <div className="flex justify-end pt-4 border-t border-border mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
