import tools
import time
class SupportAgentOrchestrator:
    """
    Orchestrates the multi-turn agentic loop between the Claude Client (or Simulator)
    and the customer support tools. Includes security gates, post-tool hooks, 
    and structured error recovery.
    """
    def __init__(self, client, refund_threshold=200.00):
        self.client = client
        self.refund_threshold = refund_threshold
        
        # In-memory session context tracking client states (identity, escalation status, etc.)
        self.session_context = {
            "customer_id": None,
            "customer_name": None,
            "is_verified": False,
            "verification_attempts": 0,
            "escalated": False,
            "escalation_reason": None,
            "escalation_summary": None,
            "transient_error_counter": {}  # Keeps track of retries for specific tools/arguments
        }
        self.messages = []
        
        # System instructions given to Claude to guide tool-use and safety behaviors
        self.system_prompt = (
            "You are a helpful, precise, and secure Customer Support Resolution Agent for a retail store.\n"
            "You have access to tools that can look up customers, retrieve order details, process refunds, and escalate requests.\n\n"
            "CRITICAL GUIDELINES:\n"
            "1. SECURITY: You MUST always call 'get_customer' and verify the customer's identity via their 6-digit verification code BEFORE calling 'lookup_order' or 'process_refund'. If they haven't provided their name, ask for it first. If they haven't provided their code, ask for it.\n"
            "2. CLARIFICATION/DISAMBIGUATION: If the customer asks to return an item they have purchased multiple times (e.g. they own several water heaters of different brands), you must present the list of orders to the user and ask them to clarify which exact item/brand they want to return.\n"
            "3. POLICY ENFORCEMENT: When checking an order, review the refund policy window that was active on the purchase date. If the return request is outside the policy window, do NOT process the refund; instead, explain this clearly and call 'escalate_to_human'.\n"
            "4. REFUND LIMITS: Any refund request exceeding $200.00 will be programmatically escalated. Try to call process_refund anyway as part of the flow; the system will safely intercept and redirect it to 'escalate_to_human'.\n"
            "5. ESCALATION: When escalating, provide a clean, structured summary containing Customer ID, Core Problem, Order/Refund Amount, and Recommended Action."
        )
    def run(self, user_message: str, log_callback=None) -> str:
        """
        Runs the conversational turn-taking loop. 
        Loops while Claude requests tool executions (stop_reason = 'tool_use').
        """
        self.messages.append({
            "role": "user",
            "content": user_message
        })
        loop_count = 0
        max_turns = 10  # Prevent infinite loops in case of model confusion
        
        while loop_count < max_turns:
            loop_count += 1
            
            # Send conversation history to the model/simulation client
            response = self.client.create_message(
                model="claude-3-5-sonnet-latest",
                messages=self.messages,
                tools=tools.SCHEMAS,
                system=self.system_prompt,
                session_context=self.session_context
            )
            
            # Record assistant turn in history
            self.messages.append({
                "role": "assistant",
                "content": response["content"]
            })
            
            if log_callback:
                log_callback("assistant_thoughts", response)
            
            # Stop condition 1: Normal message turn ended
            if response["stop_reason"] == "end_turn":
                # Find and return the text block response
                text_response = "".join(
                    [block["text"] for block in response["content"] if block["type"] == "text"]
                )
                return text_response
                
            # Stop condition 2: Model wants to use tools
            elif response["stop_reason"] == "tool_use":
                tool_calls = [block for block in response["content"] if block["type"] == "tool_use"]
                tool_results_blocks = []
                
                for tool in tool_calls:
                    tool_id = tool["id"]
                    tool_name = tool["name"]
                    tool_input = tool["input"]
                    
                    if log_callback:
                        log_callback("tool_call", {
                            "name": tool_name,
                            "input": tool_input,
                            "id": tool_id
                        })
                    
                    # --- STEP 3: Prerequisite Security Gate ---
                    # Code-level guarantee blocking lookup_order and process_refund if not verified
                    is_gated_tool = tool_name in [tools.LOOKUP_ORDER, tools.PROCESS_REFUND]
                    is_verified = self.session_context.get("is_verified", False)
                    
                    if is_gated_tool and not is_verified:
                        result = {
                            "success": False,
                            "error_category": "PERMISSION",
                            "is_retryable": False,
                            "message": (
                                f"Access Denied: You cannot call tool '{tool_name}' because the customer is not verified. "
                                "You must first call get_customer(customer_name) to initiate identity verification, "
                                "and verify their verification_code before accessing order details or processing refunds."
                            )
                        }
                    else:
                        # --- STEP 5: Run tool and handle structured errors with retries ---
                        result = self._execute_tool_with_retry(tool_name, tool_input, log_callback)
                        
                        # --- STEP 4: PostToolUse Hook ---
                        # Intercept any refund above the set threshold (e.g. $200) and redirect to human escalation
                        if tool_name == tools.PROCESS_REFUND and result.get("success") is True:
                            refund_amount = tool_input.get("amount", 0.0)
                            if refund_amount > self.refund_threshold:
                                if log_callback:
                                    log_callback("hook_intercept", {
                                        "amount": refund_amount,
                                        "threshold": self.refund_threshold
                                    })
                                
                                # Format a clean escalation summary (Step 7)
                                cust_id = self.session_context.get("customer_id", "UNKNOWN")
                                order_id = tool_input.get("order_id", "UNKNOWN")
                                escalation_summary = (
                                    f"Customer ID: {cust_id}\n"
                                    f"Core Problem: High-value refund request for order {order_id}.\n"
                                    f"Order/Refund Amount: ${refund_amount:.2f}\n"
                                    f"Recommended Action: High-value refund requests (> ${self.refund_threshold:.2f}) must be verified manually. Check return history for potential abuse, then process manually if appropriate."
                                )
                                
                                # Overwrite the refund success result with a human escalation ticket
                                result = tools.escalate_to_human_tool(
                                    self.session_context,
                                    summary=escalation_summary,
                                    reason=f"Refund limit exceeded (Requested ${refund_amount:.2f} > Limit ${self.refund_threshold:.2f})"
                                )
                    
                    if log_callback:
                        log_callback("tool_result", {
                            "name": tool_name,
                            "result": result,
                            "id": tool_id
                        })
                    
                    tool_results_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": str(result)  # Feed result back as a string representation
                    })
                
                # Append the tool execution results back to messages to continue the loop
                self.messages.append({
                    "role": "user",
                    "content": tool_results_blocks
                })
        
        return "Support agent loop terminated: execution turn limit exceeded."
    def _execute_tool_with_retry(self, name: str, arguments: dict, log_callback=None, max_retries=3) -> dict:
        """Executes a tool with automated retry logic if transient errors occur (Step 5)."""
        retries = 0
        while retries <= max_retries:
            try:
                # Deterministic transient error simulator for testing (ORD-TRANS-999)
                if name == tools.LOOKUP_ORDER and arguments.get("order_id") == "ORD-TRANS-999":
                    counter = self.session_context["transient_error_counter"].get("ORD-TRANS-999", 0) + 1
                    self.session_context["transient_error_counter"]["ORD-TRANS-999"] = counter
                    
                    # Fail the first 2 times, succeed on the 3rd
                    if counter < 3:
                        if log_callback:
                            log_callback("transient_failure", {
                                "attempt": counter,
                                "message": "Database connection timed out (transient network error)"
                            })
                        raise ConnectionError("Database connection timed out (transient network error)")
                
                # Run the actual tool
                result = tools.execute_tool(name, arguments, self.session_context)
                
                # Handle error indicators returned directly in results (e.g. from network failures)
                if isinstance(result, dict) and result.get("error_category") == "TRANSIENT" and result.get("is_retryable") is True:
                    raise ConnectionError(result.get("message"))
                
                return result
                
            except (ConnectionError, TimeoutError) as e:
                retries += 1
                if retries > max_retries:
                    # Exceeded retries, return a permanent failure category
                    return {
                        "success": False,
                        "error_category": "TRANSIENT",
                        "is_retryable": False,
                        "message": f"Transient error persisted after {max_retries} retries. Directing to human. Error: {str(e)}"
                    }
                # Wait briefly before retrying
                time.sleep(0.1)
                if log_callback:
                    log_callback("retry", {
                        "attempt": retries,
                        "max_retries": max_retries,
                        "error": str(e)
                    })
            except Exception as e:
                # Permanent validation or programmatic exception, do not retry
                return {
                    "success": False,
                    "error_category": "VALIDATION",
                    "is_retryable": False,
                    "message": f"Tool execution error: {str(e)}"
                }
