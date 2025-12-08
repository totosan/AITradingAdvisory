import { MainLayout } from "@/components/layout";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    </QueryClientProvider>
  );
}

export default App;
