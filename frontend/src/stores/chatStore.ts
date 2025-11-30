import { create } from 'zustand';
import type { Message, Conversation } from '@/types/api';
import { generateId } from '@/lib/utils';

interface ChatState {
  // Current conversation
  conversationId: string | null;
  messages: Message[];
  isLoading: boolean;
  isProcessing: boolean;
  finalResult: string | null;
  
  // Conversation list
  conversations: Conversation[];
  
  // Actions
  addMessage: (message: Omit<Message, 'id'>) => void;
  updateLastMessage: (content: string) => void;
  setLoading: (loading: boolean) => void;
  setIsProcessing: (processing: boolean) => void;
  setFinalResult: (result: string | null) => void;
  setConversationId: (id: string | null) => void;
  clearMessages: () => void;
  startNewConversation: () => string;
}

export const useChatStore = create<ChatState>((set) => ({
  conversationId: null,
  messages: [],
  isLoading: false,
  isProcessing: false,
  finalResult: null,
  conversations: [],
  
  addMessage: (message) => {
    const newMessage: Message = {
      ...message,
      id: generateId(),
    };
    set((state) => ({
      messages: [...state.messages, newMessage],
    }));
  },
  
  updateLastMessage: (content) => {
    set((state) => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        messages[messages.length - 1] = { ...lastMessage, content };
      }
      return { messages };
    });
  },
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  
  setFinalResult: (result) => set({ finalResult: result }),
  
  setConversationId: (id) => set({ conversationId: id }),
  
  clearMessages: () => set({ messages: [], conversationId: null, finalResult: null }),
  
  startNewConversation: () => {
    const id = generateId();
    set({ conversationId: id, messages: [] });
    return id;
  },
}));
