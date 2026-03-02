import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import CEOChatClient from "./chat-client";

export default async function CEOChatPage() {
    const session = await auth();

    if (!session?.user) {
        redirect("/login?callbackUrl=/ceo-chat");
    }

    return <CEOChatClient />;
}
