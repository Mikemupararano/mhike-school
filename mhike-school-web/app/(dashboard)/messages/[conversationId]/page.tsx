interface MessagePageProps {
    params: {
        conversationId: string;
    };
}

export default function ConversationPage({
    params,
}: MessagePageProps) {
    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold">
                Conversation #{params.conversationId}
            </h1>

            <div className="mt-6 border rounded-xl p-4 h-[500px]">
                <p className="text-gray-500">
                    Message thread coming soon...
                </p>
            </div>
        </div>
    );
}