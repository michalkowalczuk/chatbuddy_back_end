import vertexai.preview
from google.oauth2.service_account import Credentials
from vertexai.preview.generative_models import Content, Part
from vertexai.preview.generative_models import GenerativeModel, Image


def main():
    model_id = "gemini-1.5-pro-preview-0409"
    project_id = "chatbuddy-420408"
    region = "us-central1"

    vertexai.init(project=project_id, location=region,
                  credentials=Credentials.from_service_account_file('google_sa.json'))

    system_instr = ["""
        User messages are structured as follows:
        
        <event> This will describe user event for context </event>
        <message> This is actual message from the user you should respond to </message>
        
    """]

    generative_multimodal_model = GenerativeModel(model_id,
                                                  system_instruction=system_instr)

    history = [
        Content(role="user", parts=[Part.from_text(user_message(message="hi pal!"))]),
        Content(role="model", parts=[Part.from_text("Hey man, what is up?!")]),
        Content(role="user",
                parts=[Part.from_text(user_message(message="not much, can you tell me something funny?"))]),
        Content(role="model", parts=[Part.from_text(
            "I just heard a joke about paper, but it was tearable. \n\nWhat about you? What\'s going on today? \n")]),
        Content(role="user", parts=[Part.from_text(user_message(event="User opens the chat again after 1 hour"))])
    ]

    response = generative_multimodal_model.generate_content(history)

    print(response.candidates[0].text)


def user_message(event="", message=""):
    return f"""
        <event>{event}</event>
        <message>{message}</message>
    """


if __name__ == "__main__":
    main()
