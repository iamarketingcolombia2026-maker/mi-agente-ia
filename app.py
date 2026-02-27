from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr
import base64


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

def push(text):
    print(f"DEBUG: Enviando a Pushover: {text}", flush=True)
    response = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )
    print(f"DEBUG: Respuesta de Pushover: {response.status_code} - {response.text}", flush=True)


def record_user_details(email, name="Nombre no indicado", notes="no proporcionadas"):
    print(f"DEBUG: Llamando a record_user_details con email={email}, name={name}, notes={notes}", flush=True)
    push(f"Registrando {name} con email {email} y notas {notes}")
    print("DEBUG: Pushover enviado para record_user_details", flush=True)
    return {"recorded": "ok"}

def record_phone_number(phone, name="Nombre no indicado", email="no proporcionado"):
    print(f"DEBUG: Llamando a record_phone_number con phone={phone}, name={name}, email={email}", flush=True)
    push(f"Registrando teléfono: {phone} - Nombre: {name} - Email: {email}")
    print("DEBUG: Pushover enviado para record_phone_number", flush=True)
    return {"recorded": "ok"}

def record_unknown_question(question):
    print(f"DEBUG: Llamando a record_unknown_question con question={question}", flush=True)
    push(f"Registrando {question}")
    print("DEBUG: Pushover enviado para record_unknown_question", flush=True)
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Utiliza esta herramienta para registrar que un usuario está interesado en estar en contacto y proporcionó una dirección de correo electrónico.",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "La dirección de email del usuario"
            },
            "name": {
                "type": "string",
                "description": "El nombre del usuario, si se indica"
            }
            ,
            "notes": {
                "type": "string",
                "description": "¿Alguna información adicional sobre la conversación que valga la pena registrar para dar contexto?"
            }
        },
        "required": ["email"]
    }
}

record_phone_number_json = {
    "name": "record_phone_number",
    "description": "Utiliza esta herramienta para registrar el número de teléfono de un usuario que desea ser contactado.",
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "description": "El número de teléfono del usuario"
            },
            "name": {
                "type": "string",
                "description": "El nombre del usuario, si se indica"
            },
            "email": {
                "type": "string",
                "description": "El correo electrónico del usuario, si se indica"
            },
        },
        "required": ["phone"]
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Utiliza siempre esta herramienta para registrar cualquier pregunta que no haya podido responder porque no se sabía la respuesta.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "La pregunta no sabe responderse"
            },
        },
        "required": ["question"]
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_phone_number_json},
        {"type": "function", "function": record_unknown_question_json}]


class Me:

    def __init__(self):
        self.api_ready = False
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("ERROR: Falta OPENAI_API_KEY. El modo IA no funcionará.")
            self.openai = None
        else:
            try:
                self.openai = OpenAI(api_key=api_key)
                self.api_ready = True
            except Exception as e:
                print(f"ERROR al inicializar OpenAI: {e}")
                self.openai = None

        self.name = "Johan David Arango Olarte"

        linkedin_path = os.path.join(BASE_DIR, "me", "Linkedin.pdf")
        summary_path = os.path.join(BASE_DIR, "me", "summary.txt")

        self.linkedin = ""
        try:
            reader = PdfReader(linkedin_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    self.linkedin += text
        except Exception as e:
            print(f"Advertencia: no se pudo leer {linkedin_path}: {e}")

        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                self.summary = f.read()
        except Exception as e:
            print(f"Advertencia: no se pudo leer {summary_path}: {e}")
            self.summary = ""


    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            try:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                print(f"Tool llamado: {tool_name} con args: {arguments}", flush=True)
                
                # Llamar a la función correspondiente
                if tool_name == "record_user_details":
                    result = record_user_details(
                        email=arguments.get("email", ""),
                        name=arguments.get("name", "No proporcionado"),
                        notes=arguments.get("notes", "No hay notas adicionales")
                    )
                    # Mensaje de confirmación más inteligente
                    confirmation = f"¡Perfecto! He recibido tu información de contacto. Te contactaré pronto por correo electrónico."
                    if arguments.get("name") != "No proporcionado":
                        confirmation = f"¡Gracias {arguments['name']}! He recibido tu información y te contactaré pronto."
                    results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"status": "success", "message": confirmation, **result})
                    })
                    
                elif tool_name == "record_phone_number":
                    result = record_phone_number(
                        phone=arguments.get("phone", ""),
                        name=arguments.get("name", "No proporcionado"),
                        email=arguments.get("email", "No proporcionado")
                    )
                    # Mensaje de confirmación más inteligente
                    confirmation = f"¡Excelente! He anotado tu número de teléfono y te contactaré lo antes posible."
                    if arguments.get("name") != "No proporcionado":
                        confirmation = f"¡Perfecto {arguments['name']}! He guardado tu número y te llamaré pronto."
                    results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({
                            "status": "success", 
                            "message": confirmation, 
                            **result
                        })
                    })
                    
                elif tool_name == "record_unknown_question":
                    result = record_unknown_question(arguments.get("question", ""))
                    # Mensaje más inteligente para preguntas desconocidas
                    confirmation = "Esa es una excelente pregunta. Déjame investigarla más a fondo para darte una respuesta precisa. ¿Podrías dejarme tu correo electrónico para contactarte con la información detallada?"
                    results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({
                            "status": "success",
                            "message": confirmation,
                            **result
                        })
                    })
                    
            except Exception as e:
                print(f"Error en handle_tool_call: {str(e)}", flush=True)
                results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"status": "error", "message": str(e)})
                })
        
        return results
        
    def system_prompt(self):
        system_prompt = f"""Me llamo Johan David Arango Olarte. Soy Estratega digital en configurar y solucionar problemas para publicar en ADS trabajo en aumentar ventas con IA y marketing digital B2B & B2C.
            
            Actúas como {self.name}. Respondes preguntas en el sitio web de {self.name}.
            Tu responsabilidad es representar a {self.name} en las interacciones del sitio web con la mayor fidelidad posible.
            Se te proporciona un resumen de la trayectoria profesional y el perfil de LinkedIn de {self.name} que debes usar para responder preguntas.
            Eres libre de conversar de forma natural y responder preguntas generales sobre ti. Si no sabes un dato personal específico, puedes responder con naturalidad y cortesía sin necesidad de evadir la pregunta.
            
            INSTRUCCIONES ESPECÍFICAS:
            1. Si el usuario proporciona un número de teléfono, usa la herramienta 'record_phone_number' para registrarlo.
            2. Si el usuario proporciona un correo electrónico, usa la herramienta 'record_user_details' para registrarlo.
            3. Si la pregunta es realmente difícil, técnica, y definitivamente está fuera de tu conocimiento profesional o del contexto de los documentos proporcionados, usa la herramienta 'record_unknown_question' para registrarla. NO uses esta herramienta para preguntas casuales.
            4. Siempre confirma al usuario que has recibido su información de contacto o que has registrado su pregunta para seguimiento."""
        
        system_prompt += f"\n\n## Resumen:\n{self.summary}\n\n## Perfil de LinkedIn:\n{self.linkedin}\n\n"
        system_prompt += f"En este contexto, por favor chatea con el usuario, manteniéndote siempre en el personaje de {self.name}."
        return system_prompt
    
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def chat(self, message, history):
        if not self.api_ready or not self.openai:
            return "Lo siento, el sistema de IA no está configurado correctamente (falta API Key o es inválida). Por favor, contacta al administrador o intenta usar la opción de WhatsApp Directo."

        messages = [{"role": "system", "content": self.system_prompt()}]
        
        # Handle multimodal input
        user_content = []
        
        # message can be a string (text only) or a dict (text + files)
        if isinstance(message, dict):
            text = message.get("text", "")
            files = message.get("files", [])
            
            if text:
                user_content.append({"type": "text", "text": text})
                
            for file_path in files:
                # Check for image extensions
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    base64_image = self.encode_image(file_path)
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    })
                else:
                    user_content.append({"type": "text", "text": f"\\n[Archivo adjunto: {file_path}]"})
        else:
            # Fallback for text-only
            user_content = str(message)

        messages.append({"role": "user", "content": user_content})
            
        print(f"Mensaje a enviar a OpenAI: {len(messages)} mensajes")

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
            )
            
            # Verificar si hay tool_calls en la respuesta
            if response.choices[0].message.tool_calls:
                print(f"DEBUG: Tool calls detectados: {len(response.choices[0].message.tool_calls)}", flush=True)
                tool_results = self.handle_tool_call(response.choices[0].message.tool_calls)
                
                # Agregar los resultados de las herramientas al historial y hacer otra llamada
                messages.append(response.choices[0].message)
                messages.extend(tool_results)
                
                # Segunda llamada para obtener la respuesta final
                final_response = self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tools,
                )
                return final_response.choices[0].message.content
            else:
                return response.choices[0].message.content
        except Exception as e:
            print(f"ERROR OpenAI API: {str(e)}", flush=True)
            return f"Hubo un error de conexión con la IA: {str(e)}"
    

if __name__ == "__main__":
    print("Iniciando la aplicación...")
    me = Me()
    print("Aplicación iniciada. Abre http://localhost:8002 en tu navegador.")
    
    with gr.Blocks() as demo:
        # Inject CSS and JS via HTML component for reliability
        gr.HTML("""
        <style>
            /* === RESET & BASE === */
            body, .gradio-container {
                margin: 0 !important;
                padding: 0 !important;
                width: 100% !important;
                height: 100vh !important;
                overflow: hidden !important;
                display: flex !important;
                flex-direction: column !important;
                background: #efeae2 !important; /* Standard Light Background */
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
            }
            
            footer, header { display: none !important; }
            h1, h2, h3 { display: none !important; }
            .show-api { display: none !important; }

            /* === BUBBLES BASE (LIGHT THEME - DEFAULT) === */
            .message-row { background: transparent !important; border: none !important; padding: 4px 0 !important; margin-bottom: 4px !important; }
            .message { border: none !important; max-width: 85% !important; font-size: 15px !important; box-shadow: 0 1px 0.5px rgba(0,0,0,0.1) !important; }
            
            /* Bot Bubble (White) */
            .message.bot { 
                background-color: #ffffff !important; 
                color: #111b21 !important; 
                border-radius: 0px 12px 12px 12px !important; 
                margin-right: auto !important; 
            }
            .message.bot * { color: #111b21 !important; } /* Force black text */

            /* User Bubble (Light Green) */
            .message.user { 
                background-color: #d9fdd3 !important; 
                color: #111b21 !important; 
                border-radius: 12px 12px 0px 12px !important; 
                margin-left: auto !important; 
            }
            .message.user * { color: #111b21 !important; } /* Force black text */

            /* Remove Avatars */
            .avatar-container { display: none !important; }

            /* INPUT AREA - LIGHT MODE */
            .row { background-color: #f0f2f5 !important; padding: 10px !important; }
            .wrap { background-color: #ffffff !important; border-radius: 24px !important; border: none !important; padding: 4px 15px !important; }
            textarea { color: #111b21 !important; background: transparent !important; font-size: 15px !important; }
            textarea::placeholder { color: #8696a0 !important; }
            
            /* Send Button */
            button.primary { background-color: #00a884 !important; color: #ffffff !important; border-radius: 50% !important; border: none !important; }

            /* === DASHBOARD MODE OVERRIDES (DARK THEME) === */
            body.dashboard-mode { background: #0b141a !important; }
            body.dashboard-mode .gradio-container { background: #0b141a !important; }
            
            body.dashboard-mode .message.bot { background-color: #202c33 !important; color: #ffffff !important; }
            body.dashboard-mode .message.bot * { color: #ffffff !important; }

            body.dashboard-mode .message.user { background-color: #005c4b !important; color: #ffffff !important; }
            body.dashboard-mode .message.user * { color: #ffffff !important; }

            body.dashboard-mode .row { background-color: #202c33 !important; }
            body.dashboard-mode .wrap { background-color: #2a3942 !important; }
            body.dashboard-mode textarea { color: #ffffff !important; }
            
            /* Clean up Gradio default tabs */
            .tabs { border: none !important; }
            .tab-nav { display: none !important; }
        </style>
        
        <script>
            function setViewMode() {
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('view') === 'dashboard') {
                    document.body.classList.add('dashboard-mode');
                    document.body.classList.remove('public-mode');
                } else {
                    document.body.classList.add('public-mode');
                    document.body.classList.remove('dashboard-mode');
                }
            }
            window.addEventListener('load', setViewMode);
            setInterval(setViewMode, 500);
        </script>
        """)

        # Chat Interface fills available space
        with gr.Group(elem_classes="chat-interface"):
            gr.ChatInterface(
                me.chat,
                title="",
                description=None,
                retry_btn=None,
                undo_btn=None,
                clear_btn=None,
                submit_btn="➤",
                multimodal=True,
            )

        # Compact Footer at the bottom
        gr.HTML("""
        <div style="text-align: center; padding: 8px; background: #f0fdf4; border-top: 1px solid #dcfce7;">
            <p style="margin: 0; font-size: 11px; color: #166534; line-height: 1.2;">
                ¿Atención inmediata? <strong>Escribe tu número</strong> y te contactamos.
            </p>
        </div>
        """)
# We need FastAPI to inject CORS headers properly for external domains
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

me_instance = Me()

@app.get("/ping")
async def ping():
    return {"status": "ok", "api_ready": me_instance.api_ready}

@app.get("/debug")
async def debug():
    key = os.getenv("OPENAI_API_KEY")
    return {
        "api_ready": me_instance.api_ready,
        "key_present": bool(key),
        "key_prefix": key[:4] + "..." if key else None,
        "env_vars": list(os.environ.keys())[:10], # Show first 10 keys for context
        "base_dir": BASE_DIR
    }

@app.post("/api/chat")
async def api_chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        history = data.get("history", [])
        
        print(f"DEBUG API: Request received. Message: {message}")
        
        if not me_instance.api_ready:
            print("ERROR API: OpenAI API not ready (check API Key in Render Environment Variables)")
            return JSONResponse(content={"output": "Error: El servidor no tiene configurada la API KEY de OpenAI.", "status": "error"}, status_code=500)

        reply = me_instance.chat(message, history)
        print(f"DEBUG API: AI Reply generated (len={len(reply)})")
        
        return JSONResponse(content={
            "output": reply,
            "status": "success"
        })
    except Exception as e:
        print(f"ERROR API: {str(e)}")
        return JSONResponse(content={
            "output": f"Error en el servidor del agente: {str(e)}",
            "status": "error"
        }, status_code=500)

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    print("Iniciando con soporte CORS en el puerto 8003...")
    uvicorn.run(app, host="0.0.0.0", port=8003)

