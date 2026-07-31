import { Navigate, Route, Routes } from 'react-router-dom';
import { NavProvider } from './components/PageTransition';
import { AdminLayout } from './components/admin/AdminLayout';
import { RequireAdminAuth } from './lib/adminAuth';
import { AvatarManage } from './pages/admin/AvatarManage';
import { AdminManage } from './pages/admin/AdminManage';
import { Dashboard } from './pages/admin/Dashboard';
import { ConversationManage } from './pages/admin/ConversationManage';
import { SpotManage } from './pages/admin/SpotManage';
import { TicketManage } from './pages/admin/TicketManage';
import { FavoriteManage } from './pages/admin/FavoriteManage';
import { OrderManage } from './pages/admin/OrderManage';
import { FeedbackManage } from './pages/admin/FeedbackManage';
import { FaqManage } from './pages/admin/FaqManage';
import { KnowledgeManage } from './pages/admin/KnowledgeManage';
import { Settings } from './pages/admin/Settings';
import { UserManage } from './pages/admin/UserManage';
import { Statistics } from './pages/admin/Statistics';
import { ConsumptionAnalysis } from './pages/admin/ConsumptionAnalysis';
import { SentimentReport } from './pages/admin/SentimentReport';
import { FavoritesPage } from './pages/FavoritesPage';
import { FaqPage } from './pages/FaqPage';
import { ChatPage } from './pages/ChatPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { GuidePage } from './pages/GuidePage';
import { HistoryConversation } from './pages/HistoryConversation';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { MobileLayout } from './pages/MobileLayout';
import { ProfilePage } from './pages/ProfilePage';
import { RegisterPage } from './pages/RegisterPage';
import { TicketPage } from './pages/TicketPage';
import { OrdersPage } from './pages/OrdersPage';

export default function App() {
  return (
    <NavProvider>
      <Routes>
        {/* Admin management backend (full-screen, no bottom nav) — protected by auth guard */}
        <Route path="/admin" element={<RequireAdminAuth><AdminLayout /></RequireAdminAuth>}>
          <Route index element={<Dashboard />} />
          <Route path="knowledge" element={<KnowledgeManage />} />
          <Route path="avatar" element={<AvatarManage />} />
          <Route path="feedback" element={<FeedbackManage />} />
          <Route path="faqs" element={<FaqManage />} />
          <Route path="statistics" element={<Statistics />} />
          <Route path="consumption" element={<ConsumptionAnalysis />} />
          <Route path="settings" element={<Settings />} />
          <Route path="users" element={<UserManage />} />
          <Route path="admins" element={<AdminManage />} />
          <Route path="conversations" element={<ConversationManage />} />
          <Route path="spots" element={<SpotManage />} />
          <Route path="tickets" element={<TicketManage />} />
          <Route path="favorites" element={<FavoriteManage />} />
          <Route path="orders" element={<OrderManage />} />
          <Route path="sentiment" element={<SentimentReport />} />
        </Route>

        {/* Auth pages (no bottom nav) */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />

        {/* Full-screen pages (no bottom nav) */}
        <Route path="/ai-chat" element={<ChatPage />} />
        <Route path="/chat" element={<Navigate to="/ai-chat" replace />} />
        <Route path="/history" element={<HistoryConversation />} />
        <Route path="/favorites" element={<FavoritesPage />} />
        <Route path="/faq" element={<FaqPage />} />
        <Route path="/tickets" element={<TicketPage />} />
        <Route path="/orders" element={<OrdersPage />} />

        {/* Mobile app shell with bottom navigation */}
        <Route element={<MobileLayout />}>
          <Route path="/home" element={<HomePage />} />
          <Route path="/guide" element={<GuidePage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/home" replace />} />
      </Routes>
    </NavProvider>
  );
}




