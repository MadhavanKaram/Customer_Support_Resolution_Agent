import os
from dotenv import load_dotenv
from client import ClaudeClient
from agent import SupportAgentOrchestrator
import sys
# Try importing rich for premium terminal formatting. If not available, fall back to print.
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.theme import Theme
    from rich.text import Text
    from rich.align import Align
    USE_RICH = True
except ImportError:
    USE_RICH = False
# Setup custom styling
if USE_RICH:
    custom_theme = Theme({
        "info": "dim cyan",
        "thought": "italic green",
        "tool_call": "bold yellow",
        "tool_res": "bold magenta",
        "hook": "bold red",
        "error": "bold red",
        "retry": "bold yellow",
        "success": "bold green",
        "final": "bold white",
        "header": "bold cyan"
    })
    console = Console(theme=custom_theme)
else:
    class DummyConsole:
        def print(self, text, style=None):
            print(text)
    console = DummyConsole()
def print_welcome():
    if USE_RICH:
        title = Text("CUSTOMER SUPPORT RESOLUTION AGENT", style="header")
        subtitle = Text("Powered by Claude API & Programmatic Safety Guardrails", style="info")
        console.print(Panel(Align.center(Text.assemble(title, "\n", subtitle)), border_style="cyan"))
    else:
        print("="*60)
        print("      CUSTOMER SUPPORT RESOLUTION AGENT (CLAUDE API)")
        print("="*60)
def log_agent_step(step_type: str, data: dict):
    """Callback function to output agent internals visually."""
    if step_type == "assistant_thoughts":
        return
        # Extract and print thought text block
        text_blocks = [block["text"] for block in data["content"] if block["type"] == "text"]
        if text_blocks and text_blocks[0].strip():
            if USE_RICH:
                console.print(Panel(
                    Text(text_blocks[0].strip(), style="thought"), 
                    title="[bold green]Claude's Chain-of-Thought[/bold green]", 
                    border_style="green"
                ))
            else:
                print(f"\n[Claude's Thought] {text_blocks[0].strip()}")
                
    elif step_type == "tool_call":
        if USE_RICH:
            console.print(f"[tool_call]🛠️  Calling Tool:[/tool_call] [bold]{data['name']}[/bold] with arguments: {data['input']}")
        else:
            print(f"🛠️  Calling Tool: {data['name']} | Args: {data['input']}")
            
    elif step_type == "tool_result":
        status = "🟢 SUCCESS" if data["result"].get("success") else "🔴 FAILURE"
        if USE_RICH:
            console.print(f"[tool_res]↩️  Tool Result ({status}):[/tool_res] {data['result']}")
        else:
            print(f"↩️  Tool Result ({status}): {data['result']}")
            
    elif step_type == "hook_intercept":
        msg = f"⚠️  [PostToolUse Hook] Intercepted refund of ${data['amount']:.2f} (Threshold: ${data['threshold']:.2f}). Directing request to Human Escalation!"
        if USE_RICH:
            console.print(Panel(Text(msg, style="hook"), border_style="red"))
        else:
            print(msg)
            
    elif step_type == "transient_failure":
        msg = f"🔌 [Transient Failure] Attempt {data['attempt']} failed: {data['message']}. Simulating transient network failure..."
        if USE_RICH:
            console.print(f"[error]{msg}[/error]")
        else:
            print(msg)
            
    elif step_type == "retry":
        msg = f"🔄 [Loop Recovery] Encountered transient error. Performing automated retry {data['attempt']}/{data['max_retries']}..."
        if USE_RICH:
            console.print(f"[retry]{msg}[/retry]")
        else:
            print(msg)
def run_interaction(orchestrator, user_prompt: str):
    if USE_RICH:
        console.print(f"\n[bold blue]👤 Customer:[/bold blue] {user_prompt}")
    else:
        print(f"\n👤 Customer: {user_prompt}")
        
    final_reply = orchestrator.run(user_prompt, log_callback=log_agent_step)
    
    if USE_RICH:
        console.print(Panel(
            Text(final_reply, style="final"), 
            title="[bold white]🤖 Final Agent Reply[/bold white]", 
            border_style="blue"
        ))
    else:
        print(f"🤖 Agent: {final_reply}")
    # If escalated, show the ticket details
    if orchestrator.session_context.get("escalated"):
        ticket = {
            "ticket_id": orchestrator.session_context.get("escalation_summary", "").split("\n")[0].replace("Customer ID: ", "CUST-"), # fallback mock ticket
            "summary": orchestrator.session_context.get("escalation_summary"),
            "reason": orchestrator.session_context.get("escalation_reason")
        }
        if USE_RICH:
            console.print(Panel(
                Text(f"Ticket Summary:\n{ticket['summary']}\n\nEscalation Reason: {ticket['reason']}", style="error"),
                title="🚨 HUMAN ESCALATION TICKET CREATED",
                border_style="red"
            ))
        else:
            print("\n🚨 HUMAN ESCALATION TICKET CREATED")
            print(f"Summary:\n{ticket['summary']}")
            print(f"Reason: {ticket['reason']}")
def main():
    load_dotenv()
    print_welcome()
    
    client = ClaudeClient()
    
    # Showcase options
    scenarios = {
        "1": ("Asha's Blender Refund (Standard Safe Flow)", "Hi, it's Asha. My blender stopped working, I want a refund."),
        "2": ("Asha's Water Heater (Disambiguation Case)", "I bought a water heater from you, it's leaking, refund please."),
        "3": ("Laptop Refund (PostToolUse Hook Escalation)", "Hi, it's Asha. Refund my $1,200 laptop."),
        "4": ("Toaster Refund (Transient Recovery Proof)", "Hi, it's Asha. I bought a toaster from you, please refund order ORD-TRANS-999.")
    }
    
    print("\nSelect a scenario to test or chat interactively:")
    for num, (desc, _) in scenarios.items():
        print(f"  {num}. {desc}")
    print("  5. Interactive Chat Mode")
    print("  Q. Quit")
    
    choice = input("\nEnter choice: ").strip()
    if choice.lower() == 'q':
        sys.exit(0)
        
    orchestrator = SupportAgentOrchestrator(client)
    
    if choice in scenarios:
        _, prompt = scenarios[choice]
        run_interaction(orchestrator, prompt)
        
        # If it needs verification, simulate the multi-turn
        if choice == "1" and not orchestrator.session_context.get("is_verified"):
            # Asha's blender: ask for verification code next
            code = input("\nEnter verification code (Hint: 123456): ").strip()
            run_interaction(orchestrator, code)
            
        elif choice == "2":
            # Water heater refund: needs name, then verification code, then choice
            name = input("\nEnter customer name: ").strip()
            run_interaction(orchestrator, name)
            
            code = input("\nEnter verification code: ").strip()
            run_interaction(orchestrator, code)
            
            selection = input("\nWhich water heater? (1, 2, 3 or brand name): ").strip()
            run_interaction(orchestrator, selection)
            
        elif choice == "3" and not orchestrator.session_context.get("is_verified"):
            # Laptop refund: ask for verification code next
            code = input("\nEnter verification code (Hint: 123456): ").strip()
            run_interaction(orchestrator, code)
            
        elif choice == "4" and not orchestrator.session_context.get("is_verified"):
            # Toaster refund: ask for verification code next
            code = input("\nEnter verification code (Hint: 123456): ").strip()
            run_interaction(orchestrator, code)
            
    elif choice == "5":
        print("\nStarting Interactive Support Chat. Type 'exit' to end session.")
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ["exit", "quit"]:
                    break
                if not user_input:
                    continue
                run_interaction(orchestrator, user_input)
            except KeyboardInterrupt:
                break
    else:
        print("Invalid choice.")
if __name__ == "__main__":
    main()
