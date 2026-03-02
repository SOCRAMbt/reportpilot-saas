import DashboardLayout from "@/app/dashboard/layout";

export default function CEOChatLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <DashboardLayout>{children}</DashboardLayout>;
}
