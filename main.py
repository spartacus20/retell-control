from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from retell import Retell
import logging
import urllib.parse
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener variables desde el entorno
RETELL_API_KEY = os.getenv("RETELL_API_KEY", "")
INBOUND_RETELL_AGENT_ID = os.getenv("INBOUND_RETELL_AGENT_ID", "")
OUTBOUND_RETELL_AGENT_ID = os.getenv("OUTBOUND_RETELL_AGENT_ID", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
SIP_DOMAIN = os.getenv("SIP_DOMAIN", "5t4n6j0wnrl.sip.livekit.cloud")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")
SERVER_URL = os.getenv("SERVER_URL", "")
PORT = int(os.getenv("PORT", "3000"))

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
retellclient = Retell(api_key=RETELL_API_KEY)
twilioclient = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

call_data_store = {}

def make_outbound_call(to_number, from_number=None, agent_id=None, custom_variables=None, retell_llm_dynamic_variables=None):
    """
    Realiza una llamada saliente usando Twilio y conecta con un agente Retell.
    
    Args:
        to_number (str): Número de teléfono al que llamar
        from_number (str, optional): Número desde el que llamar. Por defecto usa PHONE_NUMBER de config
        agent_id (str, optional): ID del agente Retell. Por defecto usa RETELL_AGENT_ID de config
        custom_variables (dict, optional): Variables personalizadas para pasar en la URL
        retell_llm_dynamic_variables (dict, optional): Variables dinámicas para inyectar en el Response Engine prompt
        
    Returns:
        obj: Objeto de llamada Twilio o None si hay error
    """
    # Usar valores predeterminados si no se proporcionan
    if from_number is None:
        from_number = PHONE_NUMBER
        
    if agent_id is None:
        agent_id = OUTBOUND_RETELL_AGENT_ID
        
    # Inicializar variables personalizadas
    if not isinstance(custom_variables, dict):
        custom_variables = {}
    
    # Inicializar variables dinámicas para Retell
    if not isinstance(retell_llm_dynamic_variables, dict):
        retell_llm_dynamic_variables = {}
        
    # Crear string de consulta para las variables personalizadas
    query_string = urllib.parse.urlencode(custom_variables)
    
    # Obtener la URL base del servidor
    base_url = SERVER_URL
    
    try:
        # Crear la llamada con Twilio
        call = twilioclient.calls.create(
            machine_detection="Enable",
            machine_detection_timeout=8,
            async_amd="true",
            async_amd_status_callback=f"{base_url}/amd-status/{agent_id}",
            url=f"{base_url}/new-call?{query_string}",
            to=to_number,
            from_=from_number,
            status_callback=f"{base_url}/call-status",
            status_callback_event=["completed"]
        )
        
        logging.info(f"Llamada saliente iniciada - De: {from_number} A: {to_number}, SID: {call.sid}")
        
        # Registrar también la llamada con Retell
        retell_call_response = retellclient.call.register_phone_call(
            agent_id=agent_id,
            from_number=from_number,
            to_number=to_number,
            direction="outbound",
            retell_llm_dynamic_variables=retell_llm_dynamic_variables
        )
        
        # Almacenar los datos de la llamada
        call_data_store[to_number] = {
            'call_sid': call.sid,
            'retell_call_id': retell_call_response.call_id
        }
        
        return call
        
    except Exception as err:
        logging.error(f"Error al realizar llamada saliente: {err}")
        return None

@app.route('/new-call', methods=['POST'])
def new_call():
    """Handles incoming Twilio calls and initiates Retell call."""
    call_sid = request.form.get('CallSid')
    from_number = request.form.get('From')
    to_number = request.form.get('To')
    logging.info(
        f"new-call: Call SID: {call_sid}, From: {from_number}, To: {to_number}"
    )

    try:
        # Si es una llamada saliente (from_number == PHONE_NUMBER), buscamos el retell_call_id en el call_data_store
        # Si es una llamada entrante, registramos una nueva llamada con Retell
        if from_number == PHONE_NUMBER:
            # Para llamadas salientes, el retell_call_id ya debería estar en call_data_store
            if to_number in call_data_store and 'retell_call_id' in call_data_store[to_number]:
                retell_call_id = call_data_store[to_number]['retell_call_id']
                logging.info(f"new-call: Usando retell_call_id existente: {retell_call_id}")
            else:
                # Si por algún motivo no está registrado, lo registramos ahora
                retell_call_response = retellclient.call.register_phone_call(
                    agent_id=OUTBOUND_RETELL_AGENT_ID,
                    from_number=from_number,
                    to_number=to_number,
                    direction="outbound",
                    retell_llm_dynamic_variables=request.form.get('retell_llm_dynamic_variables', {}))
                retell_call_id = retell_call_response.call_id
                call_data_store[to_number] = {
                    'call_sid': call_sid,
                    'retell_call_id': retell_call_id
                }
                logging.info(f"new-call: Registrada nueva llamada saliente con Retell: {retell_call_id}")
        else:
            # Para llamadas entrantes, siempre registramos una nueva llamada con Retell
            retell_call_response = retellclient.call.register_phone_call(
                agent_id=INBOUND_RETELL_AGENT_ID,
                from_number=from_number,
                to_number=to_number,
                direction="inbound")
            retell_call_id = retell_call_response.call_id
            call_data_store[from_number] = {
                'call_sid': call_sid,
                'retell_call_id': retell_call_id
            }
            logging.info(f"new-call: Registrada nueva llamada entrante con Retell: {retell_call_id}")

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

@app.route('/call-status', methods=['POST'])
def call_status():
    """Maneja callbacks de estado de la llamada desde Twilio"""
    call_sid = request.form.get('CallSid')
    call_status = request.form.get('CallStatus')
    
    logging.info(f"call-status: SID: {call_sid}, Estado: {call_status}")
    
    # Aquí puedes agregar lógica adicional según el estado de la llamada
    # Por ejemplo, limpiar datos o registrar en base de datos
    
    return "", 200

@app.route('/create-phonecall', methods=['POST'])
def create_phonecall():
    """Endpoint para iniciar una llamada saliente"""
    data = request.get_json()
    
    to_number = data.get('to_number')
    retell_llm_dynamic_variables = data.get('retell_llm_dynamic_variables', {})
    
    if not to_number:
        return {"error": "Falta el número de destino"}, 400
        
    call = make_outbound_call(
        to_number=to_number,
        from_number=PHONE_NUMBER,
        agent_id=OUTBOUND_RETELL_AGENT_ID,
        custom_variables={},
        retell_llm_dynamic_variables=retell_llm_dynamic_variables
    )
    
    if call:
        return {"success": True, "call_sid": call.sid}, 200
    else:
        return {"success": False, "error": "Error al iniciar la llamada"}, 500

@app.route('/amd-status/<agent_id>', methods=['POST'])
def amd_status(agent_id):
    """Maneja callbacks de detección de máquinas/contestadores"""
    call_sid = request.form.get('CallSid')
    amd_result = request.form.get('AnsweredBy', 'unknown')
    
    logging.info(f"Detección de máquina para llamada {call_sid}: {amd_result}")
    
    # Aquí puedes implementar lógica basada en si es humano o máquina
    
    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
