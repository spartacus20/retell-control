from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial
from retell import Retell
from transferfunctions import transfer_mmj, transfer_trt, transfer_medical
import logging
from config import (RETELL_API_KEY, RETELL_AGENT_ID, TWILIO_ACCOUNT_SID,
                    TWILIO_AUTH_TOKEN, SIP_DOMAIN)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
retellclient = Retell(api_key=RETELL_API_KEY)
twilioclient = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
phoneNumbers = {
    "transfer_mmj": transfer_mmj,
    "transfer_medical": transfer_medical,
    "transfer_trt": transfer_trt
}
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
        retell_call_response = retellclient.call.register_phone_call(
            agent_id=RETELL_AGENT_ID,
            from_number=from_number,
            to_number=to_number,
            direction="inbound")
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


@app.route('/run-function', methods=['POST'])
def run_function():
    try:
        logging.info("run-function: Endpoint hit")
        data = request.json
        call_data = data.get('call', {})
        function_name = data.get("name")
        from_number = call_data.get('from_number')
        call_id = data.get("call_id")
        if from_number in call_data_store:
            transfer_number = phoneNumbers[function_name]()
            call_sid = call_data_store[from_number]['call_sid']
            logging.info(f"run-function: call_sid retrieved: {call_sid}")
            voice_response = VoiceResponse()
            voice_response.dial(
                transfer_number,
                callerId=from_number)  #dial the transfer number.
            twilioclient.calls(call_sid).update(
                twiml=str(voice_response))  #update the call.
            logging.info(f"run-function: Call {call_sid} transfer initiated.")
            return jsonify({
                "transfer_number": transfer_number,
                "original_call_sid": call_sid,
                "function_name": function_name,
            })
        else:
            logging.error("run-function: Call SID not found.")
            return jsonify({"error": "Call SID not found"})
    except Exception as e:
        logging.error(f"run-function: An error occurred: {e}")
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
