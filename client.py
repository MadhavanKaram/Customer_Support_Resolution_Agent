import os
import uuid
from dotenv import load_dotenv
# Try to import anthropic. If not installed, we can still run in mock mode.
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
load_dotenv()
class MockContentBlock:
    def __init__(self, type_name, text=None, id_val=None, name=None, input_dict=None):
        self.type = type_name
        self.text = text
        self.id = id_val
        self.name = name
        self.input = input_dict
    def __repr__(self):
        if self.type == "text":
            return f"MockTextBlock(text='{self.text}')"
        return f"MockToolUseBlock(id='{self.id}', name='{self.name}', input={self.input})"
class MockMessage:
    def __init__(self, content, stop_reason):
        self.id = f"msg_mock_{uuid.uuid4().hex[:8]}"
        self.type = "message"
        self.role = "assistant"
        self.content = content
        self.stop_reason = stop_reason
    def __repr__(self):
        return f"MockMessage(id='{self.id}', role='{self.role}', content={self.content}, stop_reason='{self.stop_reason}')"
class MockMessages:
    def create(self, model, max_tokens, messages, tools, system, session_context=None):
        """
        Simulates Claude's logic for the three core scenarios: Asha's blender,
        the 3 water heaters, and the $1,200 laptop.
        """
        # Extract messages history and flatten content for keyword checking
        history = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # If content is a list (e.g. from tool returns), format it simply for scanning
            if isinstance(content, list):
                summary = []
                for part in content:
                    if part.get("type") == "tool_result":
                        summary.append(f"[ToolResult:{part.get('tool_use_id')} success={part.get('content')}]")
                    else:
                        summary.append(str(part))
                history.append((role, " ".join(summary)))
            else:
                history.append((role, str(content)))
        # 1. Identify which scenario we are running based on original prompts
        first_user_message = next((msg[1] for msg in history if msg[0] == "user"), "").lower()
        
        is_blender = "blender" in first_user_message
        is_water_heater = "water heater" in first_user_message or "heater" in first_user_message
        is_laptop = "laptop" in first_user_message
        is_toaster = "toaster" in first_user_message or "transient" in first_user_message or "ord-trans-999" in first_user_message
        # Helper: check if a specific tool result exists in history
        def get_last_tool_result(tool_name):
            # Scan backwards for tool results
            for role, text in reversed(history):
                if "[ToolResult:" in text:
                    # Let's see if this result was associated with the tool
                    # For simulation, we can also inspect the previous assistant tool call
                    pass
            # Better: inspect the sequence of message logs
            return None
        # Let's count how many times we've run get_customer, lookup_order, process_refund, etc.
        # We can find this by looking at tool_results or assistant tool calls in history.
        get_customer_calls = 0
        get_customer_verified = session_context.get("is_verified", False) if session_context else False
        lookup_order_calls = 0
        process_refund_calls = 0
        escalation_calls = 0
        
        last_tool_result_content = None
        
        # Traverse messages to reconstruct the state of tool calls and results
        for msg in messages:
            content = msg["content"]
            role = msg["role"]
            if role == "assistant" and isinstance(content, list):
                for part in content:
                    # Debug print
                    # print(f"DEBUG: assistant msg part: {type(part)} -> {part}")
                    
                    # Check both dict and MockContentBlock object representation
                    t_type = part.get("type") if isinstance(part, dict) else getattr(part, "type", None)
                    t_name = part.get("name") if isinstance(part, dict) else getattr(part, "name", None)
                    
                    if t_type == "tool_use":
                        if t_name == "get_customer":
                            get_customer_calls += 1
                        elif t_name == "lookup_order":
                            lookup_order_calls += 1
                        elif t_name == "process_refund":
                            process_refund_calls += 1
                        elif t_name == "escalate_to_human":
                            escalation_calls += 1
            elif role == "user" and isinstance(content, list):
                for part in content:
                    res_content = part.get("content") if isinstance(part, dict) else getattr(part, "content", None)
                    last_tool_result_content = res_content
                    # Check if verification succeeded
                    if "successfully verified" in str(res_content) or "'is_verified': True" in str(res_content):
                        get_customer_verified = True
                    if isinstance(res_content, dict) and res_content.get("is_verified") is True:
                        get_customer_verified = True
                        
        print(f"DEBUG SUMMARY: get_customer_calls={get_customer_calls}, get_customer_verified={get_customer_verified}, lookup_order_calls={lookup_order_calls}, process_refund_calls={process_refund_calls}, escalation_calls={escalation_calls}")
        # Let's get the last user text input (excluding tool results)
        last_user_text = ""
        for role, text in reversed(history):
            if role == "user" and "[ToolResult:" not in text:
                last_user_text = text.lower()
                break
        is_escalated = (session_context.get("escalated", False) if session_context else False) or (escalation_calls >= 1)
        # Global Verification Code Interception Check:
        # If we have called get_customer at least once, and the customer is not verified, 
        # and the user's last message contains a 6-digit numeric verification code, call get_customer with it.
        import re
        code_match = re.search(r'\b\d{6}\b', last_user_text)
        if get_customer_calls >= 1 and not get_customer_verified and code_match:
            code = code_match.group(0)
            tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
            return MockMessage(
                content=[
                    MockContentBlock("text", f"Let me verify that 6-digit security code ({code}) in our system."),
                    MockContentBlock("tool_use", id_val=tool_id, name="get_customer", input_dict={"customer_name": "Asha", "verification_code": code})
                ],
                stop_reason="tool_use"
            )
        # --- SCENARIO A: Asha's Blender / Resilient Toaster Refund ---
        if is_blender or is_toaster:
            order_id = "ORD-101" if is_blender else "ORD-TRANS-999"
            item_name = "SuperBlender 3000" if is_blender else "Resilient Toaster"
            price = 89.99 if is_blender else 45.00
            item_noun = "blender" if is_blender else "toaster"
            reason = "Blender stopped working" if is_blender else "Toaster defective"
            if get_customer_calls == 0:
                # Turn 1: Ask for customer lookup
                tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                return MockMessage(
                    content=[
                        MockContentBlock("text", f"Let me look up your customer records first to verify your account so we can assist with your {item_noun} return."),
                        MockContentBlock("tool_use", id_val=tool_id, name="get_customer", input_dict={"customer_name": "Asha"})
                    ],
                    stop_reason="tool_use"
                )
            elif get_customer_calls == 1 and not get_customer_verified:
                # Turn 2: Customer found but needs verification code
                return MockMessage(
                    content=[
                        MockContentBlock("text", "Hi Asha, I found your customer profile! For security, could you please provide the 6-digit verification code sent to your email? (Hint: It is 123456)")
                    ],
                    stop_reason="end_turn"
                )
            elif get_customer_calls == 1 and get_customer_verified and lookup_order_calls == 0:
                # Turn 3: Customer is verified. Look up order.
                tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                return MockMessage(
                    content=[
                        MockContentBlock("text", f"Thank you, your identity is verified. Now I will lookup your {item_noun} order to check the purchase details."),
                        MockContentBlock("tool_use", id_val=tool_id, name="lookup_order", input_dict={"order_id": order_id})
                    ],
                    stop_reason="tool_use"
                )
            elif get_customer_calls == 2 and get_customer_verified and lookup_order_calls == 0:
                tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                return MockMessage(
                    content=[
                        MockContentBlock("text", f"Perfect! Your identity is successfully verified. Let me lookup your {item_noun} order details now."),
                        MockContentBlock("tool_use", id_val=tool_id, name="lookup_order", input_dict={"order_id": order_id})
                    ],
                    stop_reason="tool_use"
                )
            elif lookup_order_calls == 1 and process_refund_calls == 0 and escalation_calls == 0:
                # Turn 4: Order lookup successful. Within policy, process refund.
                tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                return MockMessage(
                    content=[
                        MockContentBlock("text", f"I've checked the details for order {order_id} ({item_name}). It was purchased on May 15/20, 2026, which is within our 30-day refund window. I will now process the refund of ${price:.2f}."),
                        MockContentBlock("tool_use", id_val=tool_id, name="process_refund", input_dict={"order_id": order_id, "amount": price, "reason": reason})
                    ],
                    stop_reason="tool_use"
                )
            elif process_refund_calls == 1:
                # Turn 5: Refund successful, final reply.
                ref_id = "REF-XXXX"
                if isinstance(last_tool_result_content, dict):
                    ref_id = last_tool_result_content.get("refund_id", "REF-MOCK")
                return MockMessage(
                    content=[
                        MockContentBlock("text", f"Great news! Your refund for the {item_name} (Order ID: {order_id}) has been approved and processed. The refund amount is ${price:.2f}. Your Refund ID is {ref_id}. It should appear in your account in 3-5 business days.")
                    ],
                    stop_reason="end_turn"
                )
        # --- SCENARIO B: Water Heater Return (Disambiguation + Policies) ---
        elif is_water_heater:
            # First, check if name has been provided
            has_name = "asha" in first_user_message or "asha" in last_user_text
            
            if not has_name and get_customer_calls == 0:
                # Ask for name
                return MockMessage(
                    content=[
                        MockContentBlock("text", "I would be happy to help you with your water heater return! To get started, could you please tell me your name?")
                    ],
                    stop_reason="end_turn"
                )
            
            if get_customer_calls == 0:
                # Call get_customer
                tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                return MockMessage(
                    content=[
                        MockContentBlock("text", "Let me search our system for your customer account details."),
                        MockContentBlock("tool_use", id_val=tool_id, name="get_customer", input_dict={"customer_name": "Asha"})
                    ],
                    stop_reason="tool_use"
                )
            elif get_customer_calls == 1 and not get_customer_verified:
                # Ask for verification code
                return MockMessage(
                    content=[
                        MockContentBlock("text", "Hi Asha, I found your customer profile. To securely access your purchase details, could you please provide your 6-digit verification code? (Hint: It is 123456)")
                    ],
                    stop_reason="end_turn"
                )
            elif get_customer_verified and lookup_order_calls == 0 and escalation_calls == 0:
                # Customer verified. Now we must disambiguate the 3 water heaters!
                # Check if the user has already selected which water heater they want (AquaFlow, ThermosMax, HeatWave)
                wants_aquaflow = "aquaflow" in last_user_text or "first" in last_user_text or "may 20" in last_user_text or "newest" in last_user_text or "recent" in last_user_text
                wants_thermosmax = "thermosmax" in last_user_text or "second" in last_user_text or "dec 10" in last_user_text or "holiday" in last_user_text
                wants_heatwave = "heatwave" in last_user_text or "third" in last_user_text or "june 1" in last_user_text or "oldest" in last_user_text or "2024" in last_user_text
                
                if not (wants_aquaflow or wants_thermosmax or wants_heatwave):
                    return MockMessage(
                        content=[
                            MockContentBlock("text", 
                                "I have successfully verified your identity. I see in your order history that you have purchased a water heater from us **three separate times**:\n\n"
                                "1. **AquaFlow Water Heater** (Order ID: `ORD-201`, purchased May 20, 2026 - $350.00)\n"
                                "2. **ThermosMax Water Heater** (Order ID: `ORD-202`, purchased Dec 10, 2025 - $450.00)\n"
                                "3. **HeatWave Eco Water Heater** (Order ID: `ORD-203`, purchased June 1, 2024 - $600.00)\n\n"
                                "Could you please tell me which of these water heater orders you want to return?"
                            )
                        ],
                        stop_reason="end_turn"
                    )
                
                # User did specify!
                target_order_id = None
                if wants_aquaflow:
                    target_order_id = "ORD-201"
                elif wants_thermosmax:
                    target_order_id = "ORD-202"
                elif wants_heatwave:
                    target_order_id = "ORD-203"
                
                tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                return MockMessage(
                    content=[
                        MockContentBlock("text", f"Understood, checking the details and refund policy for order {target_order_id}."),
                        MockContentBlock("tool_use", id_val=tool_id, name="lookup_order", input_dict={"order_id": target_order_id})
                    ],
                    stop_reason="tool_use"
                )
                
            elif lookup_order_calls >= 1 and process_refund_calls == 0 and escalation_calls == 0:
                # Check which order we looked up. We can parse it from the last tool result or last assistant message inputs.
                # Let's find which order was looked up.
                looked_up_order = None
                for msg in messages:
                    content = msg["content"]
                    if msg["role"] == "assistant" and isinstance(content, list):
                        for part in content:
                            if part.get("type") == "tool_use" and part.get("name") == "lookup_order":
                                looked_up_order = part.get("input", {}).get("order_id")
                                
                if looked_up_order == "ORD-201":
                    # AquaFlow: Price $350.00, within window, but > $200.
                    # Attempt process_refund. The PostToolUse hook will intercept this and escalate.
                    tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                    return MockMessage(
                        content=[
                            MockContentBlock("text", "I've checked order ORD-201 (AquaFlow Water Heater). It was purchased on May 20, 2026, which is within the 30-day refund window. I will now initiate the refund of $350.00."),
                            MockContentBlock("tool_use", id_val=tool_id, name="process_refund", input_dict={"order_id": "ORD-201", "amount": 350.00, "reason": "Water heater faulty/leaking"})
                        ],
                        stop_reason="tool_use"
                    )
                elif looked_up_order == "ORD-202":
                    # ThermosMax: Price $450.00, purchased 2025-12-10, window is 14 days. It is 177 days elapsed.
                    # This violates refund window. The AI should decide to escalate because it violates policy.
                    tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                    escalation_summary = (
                        "Customer ID: CUST-001\n"
                        "Core Problem: Return request for ThermosMax Water Heater (ORD-202).\n"
                        "Order/Refund Amount: $450.00\n"
                        "Recommended Action: Reject or issue store credit because return request was made 177 days after purchase, violating the strict 14-day holiday refund policy."
                    )
                    return MockMessage(
                        content=[
                            MockContentBlock("text", "I've checked the details for order ORD-202 (ThermosMax Water Heater). This was purchased on Dec 10, 2025, under a strict 14-day holiday return policy. Because this is outside the return window, I cannot process the refund automatically. I will escalate this to a human manager."),
                            MockContentBlock("tool_use", id_val=tool_id, name="escalate_to_human", input_dict={"summary": escalation_summary, "reason": "Refund policy window violation (177 days elapsed vs 14 days limit)"})
                        ],
                        stop_reason="tool_use"
                    )
                elif looked_up_order == "ORD-203":
                    # HeatWave: Price $600.00, purchased 2024-06-01, window is 60 days. It is 733 days elapsed.
                    # Violates refund window. Escalate.
                    tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                    escalation_summary = (
                        "Customer ID: CUST-001\n"
                        "Core Problem: Return request for HeatWave Water Heater (ORD-203).\n"
                        "Order/Refund Amount: $600.00\n"
                        "Recommended Action: Decline refund as it is over 2 years old, which exceeds the extended 60-day promotional return policy of 2024."
                    )
                    return MockMessage(
                        content=[
                            MockContentBlock("text", "I've checked the details for order ORD-203 (HeatWave Eco Water Heater). It was purchased on June 1, 2024, under a 60-day promotional policy. Since this is over 2 years ago, it is far outside the refund window. I will escalate this to a human agent."),
                            MockContentBlock("tool_use", id_val=tool_id, name="escalate_to_human", input_dict={"summary": escalation_summary, "reason": "Refund policy window violation (733 days elapsed vs 60 days limit)"})
                        ],
                        stop_reason="tool_use"
                    )
                    
            elif is_escalated:
                # Escalation result response
                t_id = "TCKT-XXXX"
                if isinstance(last_tool_result_content, dict):
                    t_id = last_tool_result_content.get("ticket_id", "TCKT-MOCK")
                return MockMessage(
                    content=[
                        MockContentBlock("text", f"I have successfully escalated your request to our support team. Your ticket ID is {t_id}. A representative will review the details and get back to you shortly.")
                    ],
                    stop_reason="end_turn"
                )
            elif process_refund_calls == 1:
                # Wait, process_refund for AquaFlow should have been overridden, but what if the hook escalated?
                # If the hook escalated, escalation_calls would be 1!
                pass
        # --- SCENARIO C: $1,200 Laptop Refund ---
        elif is_laptop:
            if get_customer_calls == 0:
                # Turn 1: Check customer
                tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                return MockMessage(
                    content=[
                        MockContentBlock("text", "Let me lookup your customer records to verify your identity."),
                        MockContentBlock("tool_use", id_val=tool_id, name="get_customer", input_dict={"customer_name": "Asha"})
                    ],
                    stop_reason="tool_use"
                )
            elif get_customer_calls == 1 and not get_customer_verified:
                # Turn 2: Verification code request
                return MockMessage(
                    content=[
                        MockContentBlock("text", "Hi Asha, I found your record! For verification, please provide the 6-digit code. (Hint: It is 123456)")
                    ],
                    stop_reason="end_turn"
                )
            elif get_customer_verified and lookup_order_calls == 0 and escalation_calls == 0:
                # Turn 3: Authenticated. Lookup order ORD-301.
                tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                return MockMessage(
                    content=[
                        MockContentBlock("text", "Identity verified. Now let me look up your laptop order details."),
                        MockContentBlock("tool_use", id_val=tool_id, name="lookup_order", input_dict={"order_id": "ORD-301"})
                    ],
                    stop_reason="tool_use"
                )
            elif lookup_order_calls == 1 and process_refund_calls == 0 and escalation_calls == 0:
                # Turn 4: Initiate refund of $1,200. PostToolUse hook will intercept this.
                tool_id = f"toolu_{uuid.uuid4().hex[:6]}"
                return MockMessage(
                    content=[
                        MockContentBlock("text", "Checking order ORD-301. It is a Dynabook ProBook 15 purchased on May 28, 2026, which is within the 30-day return window. I will now process the refund of $1200.00."),
                        MockContentBlock("tool_use", id_val=tool_id, name="process_refund", input_dict={"order_id": "ORD-301", "amount": 1200.00, "reason": "Laptop refund request"})
                    ],
                    stop_reason="tool_use"
                )
            elif is_escalated:
                # Turn 5: Escaled because refund limit exceeded
                t_id = "TCKT-XXXX"
                if isinstance(last_tool_result_content, dict):
                    t_id = last_tool_result_content.get("ticket_id", "TCKT-MOCK")
                return MockMessage(
                    content=[
                        MockContentBlock("text", f"Your refund request for the $1,200.00 laptop (Order ID: ORD-301) has been escalated to a human agent because the amount exceeds our automatic approval limit. Ticket ID: {t_id}. A team member will assist you shortly.")
                    ],
                    stop_reason="end_turn"
                )
        # Default fallback response for other inputs
        return MockMessage(
            content=[MockContentBlock("text", "I'm sorry, I'm not sure how to assist with that. Could you please specify if you're returning a blender, water heater, or laptop?")],
            stop_reason="end_turn"
        )
class MockAnthropicClient:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.messages = MockMessages()
class ClaudeClient:
    """
    A wrapper around the Anthropic API client that acts as a toggle.
    If ANTHROPIC_API_KEY is defined in environment variables, uses the real Claude SDK.
    Otherwise, automatically falls back to MockAnthropicClient for offline simulation.
    """
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            print("[INFO] Utilizing REAL Anthropic API Client.")
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.is_mock = False
        else:
            if self.api_key and not ANTHROPIC_AVAILABLE:
                print("[WARNING] ANTHROPIC_API_KEY found but 'anthropic' library is not installed. Falling back to Mock simulation.")
            else:
                print("[INFO] ANTHROPIC_API_KEY not found. Running in OFFLINE Simulation Mode.")
            self.client = MockAnthropicClient()
            self.is_mock = True
    def create_message(self, model: str, messages: list, tools: list, system: str, max_tokens: int = 1500, session_context: dict = None) -> dict:
        """Sends a request to the Claude model or simulator, returning a standard dictionary representation."""
        if self.is_mock:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
                tools=tools,
                system=system,
                session_context=session_context
            )
        else:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
                tools=tools,
                system=system
            )
        
        # Format the response consistently
        content_blocks = []
        for block in response.content:
            if block.type == "text":
                content_blocks.append({
                    "type": "text",
                    "text": block.text
                })
            elif block.type == "tool_use":
                # Convert the input schema to standard dict
                input_data = block.input
                if not isinstance(input_data, dict):
                    # In real Anthropic block, input is an object that can be cast or accessed like a dict
                    input_data = dict(input_data)
                content_blocks.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": input_data
                })
        return {
            "id": response.id,
            "role": response.role,
            "content": content_blocks,
            "stop_reason": response.stop_reason
        }
