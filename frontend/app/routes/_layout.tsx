import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MainLayout } from "../layouts/MainLayout";

const queryClient = new QueryClient();

export default function Layout() {
  return (
    <QueryClientProvider client={queryClient}>
      <MainLayout />
    </QueryClientProvider>
  );
}
