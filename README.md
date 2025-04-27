# 🤖 Retell Control

A system for managing incoming and outgoing phone calls using [Retell](https://retellai.com/) for AI voice synthesis and [Twilio](https://www.twilio.com/) for telephony.

![Retell + Twilio](https://img.shields.io/badge/Retell%20%2B%20Twilio-AI%20Calls-blue)
![Python](https://img.shields.io/badge/Python-3.11-green)
![Flask](https://img.shields.io/badge/Flask-3.0.0-red)

## 📋 Prerequisites

- Python 3.11 or higher
- Twilio account ([sign up here](https://www.twilio.com/))
- Retell account ([sign up here](https://retellai.com/))
- Twilio phone number
- Configured Retell agents (for incoming and outgoing calls)

## 🔧 Setup

### 1. Clone the repository

```bash
git clone https://github.com/spartacus20/retell-control.git
cd retell-control
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the `.env.example` file to `.env` and configure your credentials:

```bash
cp .env.example .env
```

Edit the `.env` file with your own credentials:

```
PHONE_NUMBER="your-twilio-phone-number"
RETELL_API_KEY="your-retell-api-key"
INBOUND_RETELL_AGENT_ID="your-agent-id-for-incoming-calls"
OUTBOUND_RETELL_AGENT_ID="your-agent-id-for-outgoing-calls"
TWILIO_ACCOUNT_SID="your-twilio-account-sid"
TWILIO_AUTH_TOKEN="your-twilio-auth-token"
SIP_DOMAIN="your-retell-sip-domain" # or use the default
SERVER_URL="your-server-url" # e.g. https://your-subdomain.ngrok-free.app
PORT="3000" # Port on which the server will run
```

## 🚀 Usage

### Start the server

```bash
python main.py
```

This will start the server at `http://0.0.0.0:3000` (or the port you configured).

### Expose the server to the Internet

To receive Twilio webhooks, you need to expose your server to the Internet. You can use [ngrok](https://ngrok.com/):

```bash
ngrok http 3000
```

Copy the generated HTTPS URL (e.g., `https://your-subdomain.ngrok-free.app`) and configure it as `SERVER_URL` in your `.env` file.

### Make an outgoing call

To make an outgoing call, send a POST request to the `/create-phonecall` endpoint:

```bash
curl -X POST http://localhost:3000/create-phonecall \
  -H "Content-Type: application/json" \
  -d '{"to_number": "+1234567890"}'
```

## 📁 Project Structure

- `main.py` - Main file with the Flask application and call logic
- `.env` - File with environment variables (not included in the repository)
- `.env.example` - Template for the environment variables file
- `requirements.txt` - Project dependencies

## 🔄 Call Flow

### Incoming Calls

1. Twilio receives a call to the configured phone number
2. Twilio sends a webhook to `/new-call`
3. The server registers the call with Retell
4. Retell handles the conversation using AI
5. Twilio sends a webhook to `/call-status` when the call ends

### Outgoing Calls

1. A request is sent to `/create-phonecall`
2. The server creates a call with Twilio and registers it with Retell
3. Twilio dials the recipient's number
4. When answered, Twilio sends a webhook to `/new-call`
5. The server connects the call to the Retell agent

## 📞 API Endpoints

- **POST /create-phonecall**: Initiates an outgoing call
- **POST /new-call**: Webhook for new calls (from Twilio)
- **POST /call-status**: Webhook for call statuses (from Twilio)
- **POST /amd-status/{agent_id}**: Webhook for answering machine detection

## 🤝 Contributions

Contributions are welcome. Please open an issue or pull request for suggestions or improvements.

---

Developed with ❤️ to facilitate communication through AI agents.
