import os
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "generated_panels"
OUTPUT_DIR.mkdir(exist_ok=True)
STORY_MODEL = "gemini-3.5-flash-lite"
IMAGE_MODEL = "gemini-3.1-flash-image"

st.set_page_config(page_title="ComicCraft", page_icon="🎨", layout="wide")


def get_client():
    """Create a Gemini client only when a key is configured."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        return None
    return genai.Client(api_key=api_key)


def split_panels(story_text: str):
    """Split Gemini output into numbered panel blocks, tolerating common heading styles."""
    matches = list(re.finditer(r"(?im)^\s*(?:#{1,4}\s*)?Panel\s*([1-5])\s*[:.\-]?\s*$", story_text))
    panels = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(story_text)
        body = story_text[start:end].strip()
        panels.append((int(match.group(1)), body))
    if panels:
        return panels
    # Fallback if the model did not put each panel heading on its own line.
    chunks = re.split(r"(?i)\bPanel\s*([1-5])\s*[:.\-]?", story_text)
    for i in range(1, len(chunks), 2):
        try:
            panels.append((int(chunks[i]), chunks[i + 1].strip()))
        except (ValueError, IndexError):
            continue
    return panels


def extract_image_prompt(panel_text: str) -> str:
    """Find an image prompt even when Gemini changes capitalization or numbering."""
    match = re.search(
        r"(?is)(?:^|\n)\s*(?:4\s*[.)]\s*)?image\s*prompt\s*:\s*(.*)",
        panel_text,
    )
    if match:
        prompt = match.group(1).strip()
        # Remove any accidental next numbered section from the prompt.
        prompt = re.split(r"(?im)\n\s*(?:1\s*[.)]|scene\s*:|character action\s*:|dialogue\s*:)", prompt)[0].strip()
        return prompt
    # Some responses use the heading without a colon.
    match = re.search(r"(?is)(?:^|\n)\s*4\s*[.)]\s*image\s*prompt\s*(.*)", panel_text)
    return match.group(1).strip() if match else ""


def generate_panel_image(client, image_prompt: str, panel_number: int):
    """Generate and save one image for a panel. Returns path or a readable error."""
    if not image_prompt:
        return None, "No image prompt was found for this panel."
    prompt = (
        "Create one polished comic-book illustration for a single story panel. "
        "Do not add captions, lettering, speech bubbles, borders, watermarks, or text. "
        "Use expressive characters, clear composition, vivid but balanced colors, "
        "and keep the described character appearance consistent. Scene: " + image_prompt
    )
    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )
        for part in response.parts:
            if getattr(part, "inline_data", None) is not None:
                image = part.as_image()
                image_path = OUTPUT_DIR / f"comic_panel_{panel_number}.png"
                image.save(str(image_path))
                return image_path, None
        return None, "Gemini returned no image for this panel. Try again or check image-model access."
    except Exception as exc:
        message = str(exc)
        if "429" in message:
            message = "Gemini image quota/rate limit reached. Wait a while and retry."
        elif "403" in message or "PERMISSION_DENIED" in message:
            message = "The API key does not have permission to use this image model. Check Gemini API access and billing/limits."
        elif "404" in message or "NOT_FOUND" in message:
            message = f"Image model '{IMAGE_MODEL}' was not found for this API key/API version."
        return None, message


def friendly_error(exc):
    message = str(exc)
    if "429" in message:
        return "Gemini text quota/rate limit reached. Wait and try again later."
    if "403" in message or "PERMISSION_DENIED" in message:
        return "The API key was rejected or lacks permission. Check your Gemini API key."
    if "404" in message or "NOT_FOUND" in message:
        return f"The text model '{STORY_MODEL}' was not found or is unavailable to this API key."
    return message


st.title("🎨 ComicCraft")
st.write("Create your own AI comic story with five illustrated panels.")
st.caption("✨ Turn your imagination into a comic with Gemini AI.")

with st.sidebar:
    st.header("🎨 About ComicCraft")
    st.write("ComicCraft turns a story idea into five panels with scenes, actions, dialogue, and generated illustrations.")
    st.divider()
    st.subheader("Features")
    st.write("📖 AI story generation")
    st.write("🖼️ AI comic illustrations")
    st.write("💬 Character dialogue")
    st.write("🎭 Character consistency guidance")
    st.write("📥 Download the story")
    st.caption(f"Text model: {STORY_MODEL}\nImage model: {IMAGE_MODEL}")

story_idea = st.text_area(
    "💡 Enter your comic story idea:",
    placeholder="Example: A village girl discovers a magical book and saves her town...",
    height=120,
    key="story_idea",
)
st.info("Tip: Include the main character, setting, and problem for a more specific story.")

left, right = st.columns(2)
with left:
    generate_clicked = st.button("🚀 Generate My Comic", type="primary", use_container_width=True)
with right:
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.pop("comic_story", None)
        st.session_state.pop("comic_panels", None)
        st.session_state["story_idea"] = ""
        st.rerun()

if generate_clicked:
    for panel_index in range(1, 6):
        st.session_state.pop(f"comic_panel_path_{panel_index}", None)
    if not story_idea.strip():
        st.warning("Please enter a story idea first.")
    else:
        client = get_client()
        if client is None:
            st.error("Gemini API key is missing. Copy .env.example to .env and add your key to GEMINI_API_KEY.")
            st.stop()

        prompt = f"""
Create a short comic story based on this idea:
{story_idea.strip()}

Write exactly five panels and use these headings on separate lines: Panel 1, Panel 2, Panel 3, Panel 4, Panel 5.
For every panel include these four fields, each on its own line:
1. Scene: describe what is happening.
2. Character action: describe the action and emotion.
3. Dialogue: short natural dialogue, or 'No dialogue' if not needed.
4. Image Prompt: a detailed visual prompt for one comic illustration.

Keep the same character names, ages, appearance, hairstyle, clothing, and personality across all panels.
The image prompt must describe characters, clothing, background, pose, expression, lighting, and comic art style.
Do not add an introduction or conclusion outside the five panels.
"""
        with st.spinner("🤖 Writing your five-panel story..."):
            try:
                response = client.models.generate_content(model=STORY_MODEL, contents=prompt)
                story = (response.text or "").strip()
                if not story:
                    st.error("Gemini returned an empty story. Please try another prompt.")
                    st.stop()
                panels = split_panels(story)
                if not panels:
                    st.error("The story was generated, but the panel headings could not be detected. Please try again.")
                    st.text(story)
                    st.stop()
                st.session_state["comic_story"] = story
                st.session_state["comic_panels"] = panels
            except Exception as exc:
                st.error("Gemini story generation failed.")
                st.code(friendly_error(exc))
                st.stop()

if st.session_state.get("comic_story"):
    story = st.session_state["comic_story"]
    panels = st.session_state.get("comic_panels", [])
    st.success("🎉 Your comic story is ready!")
    st.markdown("## 📖 Your Comic Story")
    st.download_button(
        "📥 Download Story (.txt)",
        data=story,
        file_name="ComicCraft_Story.txt",
        mime="text/plain",
        use_container_width=True,
    )
    st.markdown("## 🖼️ Comic Panels")
    client = get_client()
    if client is None:
        st.warning("Your story is saved for this session, but the API key is no longer available for image generation.")
    else:
        for panel_number, panel_text in panels:
            with st.container(border=True):
                st.subheader(f"Panel {panel_number}")
                st.markdown(panel_text)
                image_prompt = extract_image_prompt(panel_text)
                if image_prompt:
                    # Generate each panel only once per click/session; cache path in session state.
                    cache_key = f"comic_panel_path_{panel_number}"
                    if not st.session_state.get(cache_key):
                        with st.spinner(f"🎨 Generating image for panel {panel_number}..."):
                            path, error = generate_panel_image(client, image_prompt, panel_number)
                        if path:
                            st.session_state[cache_key] = str(path)
                        else:
                            st.warning(f"Panel {panel_number} image was not generated: {error}")
                    image_path = st.session_state.get(cache_key)
                    if image_path and Path(image_path).exists():
                        st.image(image_path, caption=f"Comic Panel {panel_number}", use_container_width=True)
                else:
                    st.info("No image prompt was detected in this panel, so the illustration was skipped.")
