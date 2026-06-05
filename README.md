# Customer Support Resolution Agent

## Overview

The Customer Support Resolution Agent is an AI-powered customer service system built using Python and the Claude API architecture. The agent can autonomously resolve common customer support requests such as order lookups, refund requests, and return inquiries while enforcing strict safety policies.

The system follows an agentic workflow where the AI decides which tools to use, performs multi-step reasoning, and escalates complex cases to human support representatives when necessary.

---

## Features

### Customer Verification

* Customer identity must be verified before accessing order information.
* Verification is enforced programmatically through security gates.

### Order Lookup

* Retrieve customer order details.
* Validate ownership before exposing order information.

### Refund Processing

* Process eligible refunds automatically.
* Validate refund amounts and order ownership.

### Human Escalation

* Automatically escalate high-risk requests.
* Generate structured escalation summaries for support staff.

### Multi-Purchase Disambiguation

* Detect multiple similar purchases.
* Ask customers to identify the correct product before processing returns.

### Historical Policy Validation

* Apply refund policies that were active at the time of purchase.
* Support policy changes over time.

### Transient Error Recovery

* Automatically retry temporary failures.
* Recover from simulated network/database interruptions.

---

## Tools

### get_customer

Retrieves customer information and verifies identity.

### lookup_order

Returns order details and refund policy information.

### process_refund

Processes refund requests after validation.

### escalate_to_human

Creates escalation tickets and generates handoff summaries.

---

## Safety Mechanisms

### Verification Gate

The system blocks:

* lookup_order
* process_refund

until customer verification is completed.

### PostToolUse Hook

Any refund exceeding the configured threshold ($200) is automatically escalated to a human agent.

### Structured Error Handling

Errors are categorized as:

* TRANSIENT
* VALIDATION
* PERMISSION

The system retries transient failures automatically.

---

## Project Structure

```text
Customer_Support_Resolution_Agent/
│
├── agent.py
├── client.py
├── dataset.json
├── db.py
├── tools.py
├── main.py
├── test_agent.py
├── requirements.txt
└── README.md
```

---

## Installation

### Clone Repository

```bash
git clone <repository-url>
cd Customer_Support_Resolution_Agent
```

### Create Virtual Environment

```bash
python -m venv .venv
```

### Activate Environment

Windows:

```bash
.venv\Scripts\activate
```

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

---

## Running the Application

```bash
python main.py
```

Available scenarios:

1. Blender Refund
2. Water Heater Disambiguation
3. Laptop Refund Escalation
4. Transient Error Recovery
5. Interactive Chat

---

## Running Tests

```bash
python -m pytest -v
```

Expected Result:

```text
4 passed
```

---

## Demonstrated Scenarios

### Scenario A – Blender Refund

* Customer verification
* Order lookup
* Refund approval

### Scenario B – Water Heater Return

* Multiple purchases detected
* Product disambiguation
* Historical policy validation
* Human escalation

### Scenario C – Laptop Refund

* High-value refund
* PostToolUse hook interception
* Human escalation

### Scenario D – Toaster Refund

* Simulated transient failure
* Automatic retry recovery
* Successful refund

---

## Technologies Used

* Python
* Claude API Architecture
* Anthropic SDK
* Pytest
* Rich
* Python Dotenv

---

## Test Results

```text
===================
4 passed
===================
```

The system successfully satisfies all project requirements including agentic tool usage, verification enforcement, refund safety controls, escalation workflows, retry handling, and multi-purchase return resolution.
## Screenshots

### Blender Refund Flow

![Blender Refund](Screenshots/blender_refund.png)

### Water Heater Disambiguation

![Water Heater](Screenshots/water_heater_1.png)
![Water Heater](Screenshots/water_heater_2.png)

### Laptop Refund

![Laptop Refund](Screenshots/Laptop_refund_1.png)
![Laptop Refund](Screenshots/Laptop_refund_2.png)

### Toaster Refund

![Toaster Refund](Screenshots/Toaster_Refund.png)