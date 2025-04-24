
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from retell import Retell
import logging
from config import (
    RETELL_API_KEY,
    RETELL_AGENT_ID,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    SIP_DOMAIN,
    PHONE_NUMBER
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
retellclient = Retell(api_key=RETELL_API_KEY)
twilioclient = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

call_data_store = {}

@app.route('/new-call', methods=['POST'])
async def new_call():
    """Handles incoming Twilio calls and initiates Retell call."""
    call_sid = request.form.get('CallSid')
    from_number = request.form.get('From')
    to_number = request.form.get('To')
    logging.info(
        f"new-call: Call SID: {call_sid}, From: {from_number}, To: {to_number}"
    )

    try:
        if from_number == PHONE_NUMBER:
            retell_call_response = retellclient.call.register_phone_call(
                agent_id=RETELL_AGENT_ID,
                from_number=from_number,
                to_number=to_number,
                direction="outbound"
            )
        else:
            retell_call_response = retellclient.call.register_phone_call(
                agent_id=RETELL_AGENT_ID,
                from_number=from_number,
                to_number=to_number,
                direction="inbound"
            )
        
        retell_call_id = retell_call_response.call_id
        call_data_store[from_number] = {
            'call_sid': call_sid,
            'retell_call_id': retell_call_id
        }
        
        logging.info(
            f"new-call: Retell call initiated, retell_call_id: {retell_call_id}"
        )
        
        sip_endpoint = f"sip:{retell_call_id}@{SIP_DOMAIN}"
        logging.info(f"new-call: Dialing SIP endpoint: {sip_endpoint}")
        
        voice_response = VoiceResponse()
        voice_response.dial().sip(sip_endpoint)
        return str(voice_response)
    
    except Exception as e:
        logging.error(f"new-call: Error: {e}, type: {type(e)}")
        voice_response = VoiceResponse()
        voice_response.say("Sorry, there was an error connecting.")
        return str(voice_response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
