import pygame
import sys
import openai
import json
import os
import re

# Set up OpenAI API Key
from dotenv import load_dotenv

dotenv_path = os.path.expanduser("~/Downloads/.env")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((1000, 600))
WIDTH, HEIGHT = screen.get_width(), screen.get_height()

# Constants
CHAT_FOLDER = "chats"
BUTTON_HEIGHT = 40
FONT_SIZE = 18
scroll_offset = 0
target_scroll_offset = 0
scroll_speed = 10

# For the messages
message_scroll_offset = 0
message_target_scroll_offset = 0

settings_panel_active = False
user_input = ""
show_name_dialog = False
dialog_input_text = ""

# For the system instructions
system_instructions = ""  # The user can customize this in settings
editing_instructions = False  # Whether the user is currently editing the instruction text


MODELS = ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini"]
current_model = "gpt-4o-mini"  # default model

# Font initialization
FONT = pygame.font.SysFont("Arial", FONT_SIZE)
TITLE_FONT = pygame.font.SysFont("Arial", FONT_SIZE + 4, bold=True)

# Themes
THEMES = {
    "neon_nights": {
        "background": [(30, 0, 50), (80, 0, 100)],
        "sidebar": (40, 0, 70),
        "text": (255, 215, 230),
        "button": (100, 0, 150),
        "button_hover": (130, 0, 180),
        "dialog": (50, 0, 90),
        "user_bubble": (120, 0, 180),
        "assistant_bubble": (70, 0, 120),
    },
    "cyber_matrix": {
        "background": [(0, 30, 15), (0, 60, 30)],
        "sidebar": (0, 45, 20),
        "text": (200, 255, 200),
        "button": (0, 100, 50),
        "button_hover": (0, 150, 75),
        "dialog": (0, 75, 40),
        "user_bubble": (0, 120, 60),
        "assistant_bubble": (0, 90, 45),
    },
    "sunset_bliss": {
        "background": [(255, 140, 0), (255, 69, 0)],
        "sidebar": (255, 99, 71),
        "text": (255, 255, 255),
        "button": (255, 160, 122),
        "button_hover": (255, 182, 135),
        "dialog": (255, 140, 0),
        "user_bubble": (255, 174, 115),
        "assistant_bubble": (255, 127, 80),
    },
    "aqua_dreams": {
        "background": [(0, 128, 128), (0, 150, 150)],
        "sidebar": (0, 100, 100),
        "text": (230, 255, 255),
        "button": (0, 170, 170),
        "button_hover": (0, 190, 190),
        "dialog": (0, 140, 140),
        "user_bubble": (0, 200, 200),
        "assistant_bubble": (0, 160, 160),
    },
}
current_theme = THEMES["neon_nights"]

# Ensure Chat Directory Exists
if not os.path.exists(CHAT_FOLDER):
    os.makedirs(CHAT_FOLDER)

############################
# Helper Functions
############################

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def get_all_chats():
    chat_files = [f for f in os.listdir(CHAT_FOLDER) if f.endswith(".json")]
    return sorted(chat_files)

def create_new_chat(chat_name):
    sanitized_name = sanitize_filename(chat_name)
    new_chat_path = os.path.join(CHAT_FOLDER, f"{sanitized_name}.json")
    if os.path.exists(new_chat_path):
        raise ValueError(f"Chat '{chat_name}' already exists.")
    with open(new_chat_path, "w") as f:
        json.dump([], f)
    return new_chat_path

def load_chat(file_name):
    chat_path = os.path.join(CHAT_FOLDER, file_name)
    with open(chat_path, "r") as f:
        history = json.load(f)
        # Filter out invalid messages
        valid_history = [
            msg for msg in history
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg
        ]
    print(f"Loaded chat '{file_name}' with {len(valid_history)} messages.")  # Debug print
    return valid_history, chat_path

def save_chat(chat_history, chat_path):
    with open(chat_path, "w") as f:
        json.dump(chat_history, f, indent=4)

# Initialize Chat
active_chat_path = None
all_chats = get_all_chats()

if not all_chats:
    # If no chats exist, create a default one
    active_chat_path = create_new_chat("New Chat")
    chat_history = []
else:
    # Load the most recently listed chat
    chat_history, active_chat_path = load_chat(all_chats[-1])

# A place to store the clickable rectangles for each chat
chat_buttons = []

############################
# Drawing Functions
############################

def draw_rounded_rect(surface, color, rect, radius=10):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_gradient(surface, colors, rect):
    if len(colors) < 2:
        colors = [colors[0], colors[0]]
    color1, color2 = colors
    for y in range(rect.height):
        ratio = y / rect.height
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        pygame.draw.line(surface, (r, g, b), (rect.x, rect.y + y), (rect.x + rect.width, rect.y + y))

def render_sidebar():
    """
    Draws the sidebar (background, chat list, new chat button, settings button),
    and populates chat_buttons[] with clickable rect info for each chat.
    
    Scrolling in the sidebar is handled by scroll_offset & target_scroll_offset.
    """
    global scroll_offset, target_scroll_offset, active_chat_path, chat_buttons
    
    chat_buttons = []

    # Sidebar background
    draw_rounded_rect(screen, current_theme["sidebar"], (0, 0, 300, HEIGHT))
    
    # New Chat Button
    new_chat_rect = (10, 10, 280, BUTTON_HEIGHT)
    is_hover = new_chat_rect[0] <= mouse_x <= new_chat_rect[0]+280 and new_chat_rect[1] <= mouse_y <= new_chat_rect[1]+BUTTON_HEIGHT
    btn_color = current_theme["button_hover"] if is_hover else current_theme["button"]
    draw_rounded_rect(screen, btn_color, new_chat_rect, 15)
    screen.blit(FONT.render("New Chat", True, current_theme["text"]), (new_chat_rect[0] + 90, new_chat_rect[1] + 10))

    # Chat List with Scroll
    y_start = 70
    x_pos = 10
    chat_height = 35
    spacing = 45
    
    # We will clamp the scroll_offset so user can't scroll infinitely
    total_chat_space = len(get_all_chats()) * spacing
    visible_area = HEIGHT - 70 - 100  # from y=70 to y=HEIGHT-100 approx

    max_offset = 0
    min_offset = -(total_chat_space - visible_area) if total_chat_space > visible_area else 0
    
    # Smoothly move scroll_offset toward target_scroll_offset
    scroll_offset += (target_scroll_offset - scroll_offset) / scroll_speed

    # Now clamp the actual scroll_offset to avoid overshoot
    if scroll_offset > max_offset:
        scroll_offset = max_offset
    if scroll_offset < min_offset:
        scroll_offset = min_offset

    list_y_offset = y_start + scroll_offset
    
    for chat_file in get_all_chats():
        chat_rect = (x_pos, list_y_offset, 280, chat_height)
        is_active = (os.path.basename(active_chat_path) == chat_file)
        bg_color = current_theme["button_hover"] if is_active else current_theme["button"]
        
        draw_rounded_rect(screen, bg_color, chat_rect, 8)
        screen.blit(FONT.render(chat_file[:-5], True, current_theme["text"]), (chat_rect[0] + 10, chat_rect[1] + 8))
        
        chat_buttons.append((chat_rect, chat_file))
        
        list_y_offset += spacing

    # Settings Button
    settings_rect = (10, HEIGHT-60, 280, 40)
    is_hover = settings_rect[0] <= mouse_x <= settings_rect[0]+280 and settings_rect[1] <= mouse_y <= settings_rect[1]+40
    btn_color = current_theme["button_hover"] if is_hover else current_theme["button"]
    draw_rounded_rect(screen, btn_color, settings_rect, 15)
    screen.blit(FONT.render("Settings", True, current_theme["text"]), (settings_rect[0] + 100, settings_rect[1] + 10))

def get_total_message_height():
    """
    Returns the total pixel height needed to render all messages (for scrolling).
    We'll replicate the logic in render_messages to measure the heights
    without actually drawing.
    """
    total_height = 0
    max_width = WIDTH - 350
    
    for msg in chat_history:
        if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
            continue
        role = msg["role"]
        if role not in ["user", "assistant"]:
            continue
        
        words = msg["content"].split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if FONT.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        line_height = FONT.get_linesize()
        bubble_height = len(lines) * line_height + 20
        total_height += bubble_height + 10  # Add spacing below bubble
    return total_height

def render_messages():
    """
    Render messages as rounded-corner text bubbles that match the theme.
    Now it includes message_scroll_offset so we can scroll up/down if messages
    exceed the visible area.
    """
    # The area for messages is from x=300 to the right edge, and from y=0 to y=HEIGHT-80 (above input box).
    y_offset = 20 + message_scroll_offset  
    max_width = WIDTH - 350
    
    for msg in chat_history:
        if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
            continue
        role = msg["role"]
        if role not in ["user", "assistant"]:
            continue

        is_user = (role == "user")

        bubble_color = current_theme["user_bubble"] if is_user else current_theme["assistant_bubble"]
        text_color = current_theme["text"]
        
        # Word-wrap
        words = msg["content"].split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if FONT.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        line_height = FONT.get_linesize()
        bubble_height = len(lines) * line_height + 20
        line_widths = [FONT.size(l)[0] for l in lines]
        bubble_width = max(line_widths) + 40
        
        if is_user:
            x_pos = WIDTH - bubble_width - 20
        else:
            x_pos = 320
        
        bubble_rect = (x_pos, y_offset, bubble_width, bubble_height)
        draw_rounded_rect(screen, bubble_color, bubble_rect, 10)
        
        text_y = y_offset + 10
        for line in lines:
            text_surf = FONT.render(line, True, text_color)
            screen.blit(text_surf, (x_pos + 10, text_y))
            text_y += line_height
        
        y_offset += bubble_height + 10

def render_settings_panel():
    """
    A bigger settings panel so we can see the System Instructions box more clearly.
      - Close button
      - Theme selection
      - Model selection
      - A text box for system instructions (single-line but larger).
    """
    global editing_instructions

    panel_w = 600
    panel_h = 600
    panel_x = WIDTH//2 - panel_w//2
    panel_y = HEIGHT//2 - panel_h//2
    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    # Draw the panel background
    draw_rounded_rect(screen, current_theme["sidebar"], panel_rect, 15)

    # Title
    title = TITLE_FONT.render("Settings", True, current_theme["text"])
    screen.blit(title, (panel_x + (panel_w // 2 - title.get_width() // 2), panel_y + 20))

    # Close button
    close_btn_rect = pygame.Rect(panel_x + panel_w - 70, panel_y + 10, 60, 30)
    draw_rounded_rect(screen, current_theme["button"], close_btn_rect, 8)
    close_text = FONT.render("Close", True, current_theme["text"])
    screen.blit(close_text, (close_btn_rect.x + 5, close_btn_rect.y + 5))

    # Theming
    y_offset = panel_y + 60
    section_title = FONT.render("Theme Selector:", True, current_theme["text"])
    screen.blit(section_title, (panel_x + 30, y_offset))
    y_offset += 30

    for theme_name in THEMES:
        btn_rect = (panel_x + 50, y_offset, 200, 35)
        is_hover = btn_rect[0] <= mouse_x <= btn_rect[0] + 200 and btn_rect[1] <= mouse_y <= btn_rect[1] + 35
        btn_color = current_theme["button_hover"] if is_hover else current_theme["button"]
        draw_rounded_rect(screen, btn_color, btn_rect, 8)
        text = FONT.render(theme_name.replace("_", " ").title(), True, current_theme["text"])
        screen.blit(text, (btn_rect[0] + 10, btn_rect[1] + 5))
        y_offset += 45

    # Model selection
    y_offset += 10
    section_title = FONT.render("Model Selector:", True, current_theme["text"])
    screen.blit(section_title, (panel_x + 30, y_offset))
    y_offset += 30

    for model in MODELS:
        btn_rect = (panel_x + 50, y_offset, 200, 35)
        is_hover = btn_rect[0] <= mouse_x <= btn_rect[0] + 200 and btn_rect[1] <= mouse_y <= btn_rect[1] + 35
        # If it's the current model, highlight differently
        btn_color = current_theme["button_hover"] if model == current_model else current_theme["button"]
        draw_rounded_rect(screen, btn_color, btn_rect, 8)
        text = FONT.render(model, True, current_theme["text"])
        screen.blit(text, (btn_rect[0] + 10, btn_rect[1] + 5))
        y_offset += 45

    # System Instructions
    y_offset += 20
    section_title = FONT.render("System Instructions:", True, current_theme["text"])
    screen.blit(section_title, (panel_x + 30, y_offset))
    y_offset += 30

    instruction_rect = pygame.Rect(panel_x + 50, y_offset, 500, 60)
    box_color = current_theme["button_hover"] if editing_instructions else current_theme["button"]
    draw_rounded_rect(screen, box_color, instruction_rect, 8)

    inst_surf = FONT.render(system_instructions, True, current_theme["text"])
    screen.blit(inst_surf, (instruction_rect.x + 10, instruction_rect.y + 10))

    if not system_instructions and not editing_instructions:
        hint_surf = FONT.render("(Click here to edit instructions)", True, (180, 180, 180))
        screen.blit(hint_surf, (instruction_rect.x + 10, instruction_rect.y + 10))

def render_name_dialog():
    """
    Displays a modal dialog that asks the user to name a new chat.
    OK and Cancel buttons are placed at known offsets for easy click detection.
    """
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))
    
    dx = WIDTH//2 - 200
    dy = HEIGHT//2 - 100
    dialog_rect = (dx, dy, 400, 200)
    draw_rounded_rect(screen, current_theme["dialog"], dialog_rect, 15)
    
    title = TITLE_FONT.render("Name Your Chat", True, current_theme["text"])
    screen.blit(title, (dx + 100, dy + 20))
    
    input_rect = pygame.Rect(dx + 50, dy + 70, 300, 40)
    draw_rounded_rect(screen, current_theme["button"], input_rect, 8)
    screen.blit(FONT.render(dialog_input_text, True, current_theme["text"]), (input_rect.x + 10, input_rect.y + 10))
    
    ok_rect = pygame.Rect(dx + 100, dy + 140, 80, 35)
    draw_rounded_rect(screen, current_theme["button"], ok_rect, 8)
    screen.blit(FONT.render("OK", True, current_theme["text"]), (ok_rect.x + 25, ok_rect.y + 8))
    
    cancel_rect = pygame.Rect(dx + 220, dy + 140, 80, 35)
    draw_rounded_rect(screen, current_theme["button"], cancel_rect, 8)
    screen.blit(FONT.render("Cancel", True, current_theme["text"]), (cancel_rect.x + 10, cancel_rect.y + 8))

def render_input_box():
    input_rect = (310, HEIGHT - 70, WIDTH - 340, 50)
    draw_rounded_rect(screen, current_theme["sidebar"], input_rect, 15)
    screen.blit(FONT.render(user_input, True, current_theme["text"]), (input_rect[0]+15, input_rect[1]+15))


##############################################
# Main Loop
##############################################

clock = pygame.time.Clock()
running = True

while running:
    mouse_x, mouse_y = pygame.mouse.get_pos()
    screen.fill((0, 0, 0))
    
    # Main Background
    draw_gradient(screen, current_theme["background"], pygame.Rect(0, 0, WIDTH, HEIGHT))
    
    # Sidebar
    render_sidebar()
    
    # Compute the total message height to clamp scrolling
    total_msg_height = get_total_message_height()
    visible_height = HEIGHT - 80  # the message area is above the input box
    
    # Smoothly approach the target offset for messages
    message_scroll_offset += (message_target_scroll_offset - message_scroll_offset) / scroll_speed
    
    # Now clamp it
    if total_msg_height <= visible_height:
        message_scroll_offset = 0
        message_target_scroll_offset = 0
    else:
        max_offset = 0
        min_offset = -(total_msg_height - visible_height)
        if message_scroll_offset > max_offset:
            message_scroll_offset = max_offset
        if message_scroll_offset < min_offset:
            message_scroll_offset = min_offset
    
    # Messages
    render_messages()
    
    # Input Box
    render_input_box()
    
    # Settings Panel
    if settings_panel_active:
        render_settings_panel()
    
    # Chat Naming Dialog
    if show_name_dialog:
        render_name_dialog()
    
    # Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if active_chat_path:
                save_chat(chat_history, active_chat_path)
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if show_name_dialog:
                dx = WIDTH//2 - 200
                dy = HEIGHT//2 - 100
                ok_rect = pygame.Rect(dx + 100, dy + 140, 80, 35)
                cancel_rect = pygame.Rect(dx + 220, dy + 140, 80, 35)
                
                if ok_rect.collidepoint(mouse_x, mouse_y):
                    # OK button
                    try:
                        new_name = dialog_input_text.strip() or "New Chat"
                        active_chat_path = create_new_chat(new_name)
                        chat_history = []
                        show_name_dialog = False
                        dialog_input_text = ""
                        print(f"Created new chat: {active_chat_path}")
                    except Exception as e:
                        print(f"Error creating chat: {e}")
                
                elif cancel_rect.collidepoint(mouse_x, mouse_y):
                    # Cancel button
                    show_name_dialog = False
                    dialog_input_text = ""

            elif settings_panel_active:
                # Coordinates for the bigger settings panel
                panel_w = 600
                panel_h = 600
                panel_x = WIDTH//2 - panel_w//2
                panel_y = HEIGHT//2 - panel_h//2

                # Close button
                close_btn_rect = pygame.Rect(panel_x + panel_w - 70, panel_y + 10, 60, 30)
                if close_btn_rect.collidepoint(mouse_x, mouse_y):
                    settings_panel_active = False
                    break

                # The instructions text box
                instruction_rect = pygame.Rect(panel_x + 50,
                                               panel_y + 60 + (len(THEMES)*45 + 30) + 10 + (len(MODELS)*45 + 30) + 20 + 30,
                                               500, 60)
                if instruction_rect.collidepoint(mouse_x, mouse_y):
                    editing_instructions = True
                else:
                    editing_instructions = False

                # Themes
                y_offset = panel_y + 60 + 30
                for theme_name in THEMES:
                    btn_rect = pygame.Rect(panel_x + 50, y_offset, 200, 35)
                    if btn_rect.collidepoint(mouse_x, mouse_y):
                        current_theme = THEMES[theme_name]
                    y_offset += 45

                # Models
                y_offset += 10
                y_offset += 30
                for model in MODELS:
                    btn_rect = pygame.Rect(panel_x + 50, y_offset, 200, 35)
                    if btn_rect.collidepoint(mouse_x, mouse_y):
                        current_model = model
                    y_offset += 45

            else:
                # Check "New Chat"
                if 10 <= mouse_x <= 290 and 10 <= mouse_y <= 50:
                    show_name_dialog = True
                
                # Check "Settings"
                elif 10 <= mouse_x <= 290 and HEIGHT - 60 <= mouse_y <= HEIGHT - 20:
                    settings_panel_active = not settings_panel_active

                # Check each chat button
                else:
                    for (rect, chat_file) in chat_buttons:
                        if pygame.Rect(rect).collidepoint(mouse_x, mouse_y):
                            try:
                                save_chat(chat_history, active_chat_path)
                                chat_history, active_chat_path = load_chat(chat_file)
                            except Exception as e:
                                print(f"Error loading chat: {e}")
                            break

        elif event.type == pygame.KEYDOWN:
            if show_name_dialog:
                if event.key == pygame.K_RETURN:
                    pass
                elif event.key == pygame.K_BACKSPACE:
                    dialog_input_text = dialog_input_text[:-1]
                else:
                    dialog_input_text += event.unicode

            elif settings_panel_active and editing_instructions:
                # Editing system instructions (single-line)
                if event.key == pygame.K_BACKSPACE:
                    system_instructions = system_instructions[:-1]
                elif event.key == pygame.K_RETURN:
                    editing_instructions = False
                else:
                    system_instructions += event.unicode

            else:
                # Chat input
                if event.key == pygame.K_RETURN:
                    if user_input.strip():
                        chat_history.append({"role": "user", "content": user_input})

                        # Build the complete message set for the API
                        messages_to_send = []
                        if system_instructions.strip():
                            messages_to_send.append({"role": "system", "content": system_instructions})

                        for msg in chat_history:
                            if "role" in msg and "content" in msg:
                                messages_to_send.append(msg)

                        # Attempt calling the chosen model. If it fails, show error
                        try:
                            response = openai.ChatCompletion.create(
                                model=current_model,
                                messages=messages_to_send
                            )
                            ai_response = response.choices[0].message['content']
                            chat_history.append({"role": "assistant", "content": ai_response})
                        except Exception as e:
                            print(f"API Error: {e}")
                            chat_history.append({"role": "assistant", "content": "Error getting response"})

                        user_input = ""
                
                elif event.key == pygame.K_BACKSPACE:
                    user_input = user_input[:-1]
                else:
                    user_input += event.unicode

        elif event.type == pygame.MOUSEWHEEL:
            # Decide if the user is scrolling the sidebar or the message area
            if mouse_x < 300:
                # Mouse in sidebar region
                target_scroll_offset += event.y * 30
            else:
                # Mouse in message area
                message_target_scroll_offset += event.y * 30

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()