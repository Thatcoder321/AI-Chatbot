import pygame
import sys
import openai
import json
import os
import re



# Set up OpenAI API Key

from dotenv import load_dotenv


# Load the .env file
load_dotenv(dotenv_path="/Users/nethulkankanamge/Downloads/.env")

# Retrieve API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Debugging outputs to ensure the API key is loaded correctly
print("API Key from .env:", os.getenv("OPENAI_API_KEY"))
print("Working Directory:", os.getcwd())
# Initialize Pygame
pygame.init()


# Constants
CHAT_FOLDER = "chats"  # Folder to store chat files
BUTTON_HEIGHT = 40  # Height of the "New Chat" button
FONT_SIZE = 18

scroll_offset = 0  # Current scroll position
target_scroll_offset = 0  # Desired scroll position
scroll_speed = 10  # Speed at which the scroll catches up

# Ensure Chat Directory Exists
if not os.path.exists(CHAT_FOLDER):
    os.makedirs(CHAT_FOLDER)

# Helper Functions for Chat Management
def sanitize_filename(filename):
    """Sanitize a string to create a valid filename."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def get_all_chats():
    """Get a list of all chat files in the chats folder."""
    chat_files = [file for file in os.listdir(CHAT_FOLDER) if file.endswith(".json")]
    return sorted(chat_files)

def create_new_chat(chat_name):
    """Create a new chat file with a given name and return its path."""
    sanitized_name = sanitize_filename(chat_name)
    new_chat_name = f"{sanitized_name}.json"
    new_chat_path = os.path.join(CHAT_FOLDER, new_chat_name)
    if os.path.exists(new_chat_path):
        raise ValueError(f"A chat with the name '{chat_name}' already exists.")
    with open(new_chat_path, "w") as file:
        json.dump([], file)  # Initialize with an empty list
    return new_chat_path

def load_chat(file_name):
    """Load an existing chat."""
    chat_path = os.path.join(CHAT_FOLDER, file_name)
    with open(chat_path, "r") as file:
        return json.load(file), chat_path

def save_chat(chat_history, chat_path):
    """Save the chat history to its file."""
    with open(chat_path, "w") as file:
        json.dump(chat_history, file, indent=4)

# Initialize Chat
chat_history = []
active_chat_path = None
all_chats = get_all_chats()

if not all_chats:
    active_chat_path = create_new_chat("New Chat")
    chat_history = []
else:
    chat_history, active_chat_path = load_chat(all_chats[-1])

# Screen Dimensions
screen = pygame.display.set_mode((1000, 600))  # Wider screen for sidebar
WIDTH, HEIGHT = screen.get_width(), screen.get_height()
pygame.display.set_caption("GPT-4o Chat Manager")

# Colors
BACKGROUND_COLOR = (20, 20, 20)
SIDEBAR_COLOR = (30, 30, 30)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (90, 150, 200)
INPUT_BOX_COLOR = (40, 40, 40)
BOT_COLOR = (90, 200, 250)
USER_COLOR = (130, 190, 125)
WHITE = (255, 255, 255)
GRAY = (160, 160, 160)
ACTIVE_CHAT_HIGHLIGHT = (50, 50, 50)
scroll_offset = 0  # Tracks the vertical offset for scrolling
# Fonts
FONT = pygame.font.Font(pygame.font.match_font("arial"), FONT_SIZE)
TITLE_FONT = pygame.font.Font(pygame.font.match_font("arial"), FONT_SIZE + 4)
# User input
user_input = ""
# Draw rounded rectangles
def draw_rounded_rect(surface, color, rect, radius=10):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

# Render Sidebar
def render_sidebar():
    # Sidebar background
    draw_rounded_rect(screen, SIDEBAR_COLOR, (0, 0, 300, HEIGHT))
    
    # Render "New Chat" Button
    mouse_x, mouse_y = pygame.mouse.get_pos()
    button_color = BUTTON_HOVER_COLOR if 0 <= mouse_x <= 300 and 0 <= mouse_y <= BUTTON_HEIGHT else BUTTON_COLOR
    draw_rounded_rect(screen, button_color, (10, 10, 280, BUTTON_HEIGHT), radius=15)
    button_text = FONT.render("New Chat", True, WHITE)
    screen.blit(button_text, (125, 20))

    # Render Chat List
    y_offset = BUTTON_HEIGHT + 20
    for chat_file in get_all_chats():
        chat_name = chat_file.replace(".json", "")
        is_active = chat_file == os.path.basename(active_chat_path)
        color = WHITE if not is_active else BOT_COLOR
        bg_color = ACTIVE_CHAT_HIGHLIGHT if is_active else SIDEBAR_COLOR
        draw_rounded_rect(screen, bg_color, (10, y_offset, 280, 30), radius=10)
        chat_label = FONT.render(chat_name, True, color)
        screen.blit(chat_label, (20, y_offset + 5))
        y_offset += 40

# Render Chat Bubbles
def render_chat_history():
    total_height = 0
    y_offset = -scroll_offset  # Adjust starting position by scroll offset

    for line in chat_history:
        wrapped_lines = wrap_text(line['text'], FONT, WIDTH - 340)
        color = BOT_COLOR if line['sender'] == "bot" else USER_COLOR
        bubble_height = (FONT_SIZE + 10) * len(wrapped_lines)

        # Draw bubble
        bubble_rect = pygame.Rect(310, y_offset, WIDTH - 340, bubble_height)
        draw_rounded_rect(screen, color, bubble_rect, radius=10)

        # Draw text inside bubble
        for i, wrapped_line in enumerate(wrapped_lines):
            text = FONT.render(wrapped_line, True, WHITE)
            screen.blit(text, (320, y_offset + i * (FONT_SIZE + 5)))
        y_offset += bubble_height + 10
        total_height += bubble_height + 10

    return total_height
# Handle input dialog for chat names
def input_dialog(prompt_text):
    dialog_input = ""
    running = True
    while running:
        screen.fill((0, 0, 0))
        prompt = FONT.render(prompt_text, True, WHITE)
        screen.blit(prompt, (50, 50))
        input_box = pygame.Rect(50, 100, 400, 40)
        pygame.draw.rect(screen, WHITE, input_box, 2)
        user_text = FONT.render(dialog_input, True, WHITE)
        screen.blit(user_text, (60, 110))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return dialog_input.strip()
                elif event.key == pygame.K_BACKSPACE:
                    dialog_input = dialog_input[:-1]
                else:
                    dialog_input += event.unicode

# Chatbot Response

def draw_gradient(surface, color1, color2, rect):
    for i in range(rect.height):
        r, g, b = [
            color1[j] + (color2[j] - color1[j]) * i // rect.height
            for j in range(3)
        ]
        pygame.draw.line(surface, (r, g, b), (rect.x, rect.y + i), (rect.x + rect.width, rect.y + i))
def chatbot_response(message):
    try:
        messages = [{"role": "system", "content": "You are a helpful and polite chatbot."}]
        for chat in chat_history[-5:]:
            role = "user" if chat['sender'] == "user" else "assistant"
            messages.append({"role": role, "content": chat['text']})
        
        messages.append({"role": "user", "content": message})
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=100,
            temperature=0.7
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Wrap text
def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines

# Main Loop
GRADIENT_COLOR_1 = (20, 20, 20)  # Dark color
GRADIENT_COLOR_2 = (50, 50, 50)  
clock = pygame.time.Clock()
# Main Loop

running = True
while running:
    # Draw gradient background
    draw_gradient(screen, GRADIENT_COLOR_1, GRADIENT_COLOR_2, pygame.Rect(0, 0, WIDTH, HEIGHT))

    # Render Sidebar and Chat History
    render_sidebar()
    render_chat_history()

    # Draw Input Box
    draw_rounded_rect(screen, INPUT_BOX_COLOR, (310, HEIGHT - 60, WIDTH - 340, 40), radius=10)
    input_text = FONT.render(user_input, True, WHITE)
    screen.blit(input_text, (320, HEIGHT - 50))

    # Handle Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_chat(chat_history, active_chat_path)
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            
            # "New Chat" Button Clicked
            if 10 <= mouse_x <= 290 and 10 <= mouse_y <= BUTTON_HEIGHT:
                save_chat(chat_history, active_chat_path)
                chat_name = input_dialog("Enter a name for the new chat:")
                active_chat_path = create_new_chat(chat_name)
                chat_history = []

            # Sidebar Chat List Clicked
            elif mouse_x <= 300:  # Click is within the sidebar
                y_offset = BUTTON_HEIGHT + 20
                for chat_file in get_all_chats():
                    if y_offset <= mouse_y <= y_offset + 30:  # Click within a chat item
                        save_chat(chat_history, active_chat_path)
                        chat_history, active_chat_path = load_chat(chat_file)
                        break
                    y_offset += 40

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if user_input.strip():
                    chat_history.append({"sender": "user", "text": user_input})
                    response = chatbot_response(user_input)
                    chat_history.append({"sender": "bot", "text": response})
                user_input = ""
            elif event.key == pygame.K_BACKSPACE:
                user_input = user_input[:-1]
            else:
                user_input += event.unicode
        if event.type == pygame.MOUSEWHEEL:
            # Adjust the target scroll offset
            target_scroll_offset -= event.y * 30  # Change 30 to adjust scroll sensitivity
        # Smooth scrolling
        if scroll_offset != target_scroll_offset:
            # Move the scroll offset closer to the target
            scroll_offset += (target_scroll_offset - scroll_offset) / scroll_speed

            # Avoid floating-point imprecision by rounding
            if abs(target_scroll_offset - scroll_offset) < 1:
                scroll_offset = target_scroll_offset

        # Ensure the scroll offset stays within valid bounds
        total_height = render_chat_history()  # Get the total height of the chat
        max_scroll = max(0, total_height - HEIGHT + 60)  # Prevent overscrolling
        target_scroll_offset = max(0, min(target_scroll_offset, max_scroll))
        scroll_offset = max(0, min(scroll_offset, max_scroll))                        

    pygame.display.flip()
    clock.tick(30)