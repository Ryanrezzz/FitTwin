import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Send } from "lucide-react";
import { Button, Card, Input } from "../../components/ui.jsx";
import { useSendChat } from "./chat.api";

const AGENT = {
  route: { emoji: "🧭", label: "Router" },
  progress: { emoji: "📈", label: "Progress" },
  nutrition: { emoji: "🥗", label: "Nutrition" },
  workout: { emoji: "🏋️", label: "Workout" },
  motivation: { emoji: "🔥", label: "Motivation" },
  safety: { emoji: "🛡️", label: "Safety" },
  compose: { emoji: "✍️", label: "Compose" },
};

const QUICK = [
  "Create a vegetarian meal plan",
  "I have no dumbbells",
  "I haven't lost weight this week",
  "Give me a pep talk",
];

// minimal markdown: bold **x** + line breaks (no external lib for the MVP)
function renderText(text) {
  return text.split("\n").map((line, i) => (
    <span key={i} className="block">
      {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={j}>{part.slice(2, -2)}</strong>
        ) : (
          <span key={j}>{part}</span>
        ),
      )}
    </span>
  ));
}

function StepTrace({ steps }) {
  const agents = steps.filter((s) => AGENT[s.node] && s.node !== "compose" && s.node !== "route");
  if (agents.length === 0) return null;
  return (
    <div className="mb-2 flex flex-wrap gap-1.5">
      {agents.map((s, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
          className="rounded-full bg-ink/5 px-2 py-0.5 text-xs font-medium text-ink-soft"
          title={s.summary}
        >
          {AGENT[s.node].emoji} {AGENT[s.node].label}
        </motion.span>
      ))}
    </div>
  );
}

export default function CoachPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const send = useSendChat();
  const listRef = useRef(null);

  function scrollDown() {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    });
  }

  async function submit(text) {
    const message = (text ?? input).trim();
    if (!message || send.isPending) return;
    setMessages((m) => [...m, { role: "user", text: message }]);
    setInput("");
    scrollDown();
    try {
      const res = await send.mutateAsync(message);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: res.final?.message ?? "",
          steps: res.steps ?? [],
          intent: res.final?.intent,
        },
      ]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: `⚠️ ${err.message}`, error: true }]);
    }
    scrollDown();
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-3xl flex-col">
      <h1 className="font-display text-3xl font-extrabold tracking-tight">AI Coach</h1>
      <p className="mt-1 text-ink-soft">
        Ask anything — the orchestrator routes you to the right specialist agents.
      </p>

      <Card className="mt-4 flex min-h-0 flex-1 flex-col">
        <div ref={listRef} className="flex-1 space-y-4 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <div className="flex flex-wrap gap-2">
              {QUICK.map((q) => (
                <button
                  key={q}
                  onClick={() => submit(q)}
                  className="rounded-full border border-line px-3 py-1.5 text-sm text-ink-soft transition hover:border-volt-press hover:bg-volt/10"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={m.role === "user" ? "flex justify-end" : ""}
              >
                {m.role === "user" ? (
                  <div className="max-w-[80%] rounded-[14px] rounded-br-sm bg-ink px-3.5 py-2 text-sm text-bone">
                    {m.text}
                  </div>
                ) : (
                  <div className="max-w-[88%]">
                    {m.steps && <StepTrace steps={m.steps} />}
                    <div
                      className={`rounded-[14px] rounded-bl-sm border px-3.5 py-2.5 text-sm leading-relaxed ${
                        m.error ? "border-coral/40 bg-coral/10 text-coral" : "border-line bg-bone"
                      }`}
                    >
                      {renderText(m.text)}
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {send.isPending && (
            <div className="text-sm text-ink-soft">
              <span className="inline-flex gap-1">
                <span className="size-1.5 animate-bounce rounded-full bg-ink-soft [animation-delay:-0.2s]" />
                <span className="size-1.5 animate-bounce rounded-full bg-ink-soft [animation-delay:-0.1s]" />
                <span className="size-1.5 animate-bounce rounded-full bg-ink-soft" />
              </span>
            </div>
          )}
        </div>

        <form
          className="mt-3 flex gap-2 border-t border-line pt-3"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask your coach…"
            autoFocus
          />
          <Button type="submit" loading={send.isPending} disabled={!input.trim()}>
            <Send className="size-4" />
          </Button>
        </form>
      </Card>
    </div>
  );
}
