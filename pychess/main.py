import time
from multiprocessing import Process, Queue
import tkinter as tk
from PIL import Image, ImageTk, ImageFilter
import pygame
import engine as ChessEngine
import bot as ChessBot

BOARD_WIDTH = BOARD_HEIGHT = 1024
MOVE_LOG_PANEL_WIDTH = 520
MOVE_LOG_PANEL_HEIGHT = BOARD_HEIGHT
DIMENSION = 8
SQUARE_SIZE = BOARD_HEIGHT // DIMENSION
MAX_FPS = 60
IMAGES = {}
SOUNDS = {}

# load piece assets
def load_images() -> None:
    pieces = ["wP", "wN", "wB",  "wR", "wQ", "wK", "bP", "bN", "bB",  "bR", "bQ", "bK"]
    for piece in pieces:
        IMAGES[piece] = pygame.transform.smoothscale(pygame.image.load(f"assets/images/{piece}.png"), (SQUARE_SIZE, SQUARE_SIZE))

# load all sounds
def load_sounds() -> None:
    files = ["silence.mp3", "capture.mp3", "castle.mp3", "check.mp3", "game_end.mp3", "game_start.mp3", "move.mp3", "promote.mp3"]
    for file in files:
        name = file.split(".")[0]
        SOUNDS[name] = pygame.mixer.Sound("assets/sounds/" + file)
        SOUNDS[name].set_volume(0.75)

def draw_board(screen: pygame.display) -> None:
    global colors
    colors = [(217, 228, 232), (123, 158, 178)]
    for row in range(DIMENSION):
        for column in range(DIMENSION):
            color = colors[((row + column) % 2)]
            pygame.draw.rect(screen, color, pygame.Rect(column * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

def highlight_squares(screen: pygame.display, game_state: ChessEngine.GameState, valid_moves: list[ChessEngine.Move], square_selected: tuple[int, int], last_move: ChessEngine.Move = None) -> None:
    if square_selected != ():
        row, column = square_selected
        if game_state.board[row, column][0] == ("w" if game_state.white_to_move else "b"): # square selected is own color's piece
            # highlight selected square
            surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE))
            surface.set_alpha(100) # transparancy
            surface.fill(pygame.Color("lightslateblue"))
            screen.blit(surface, (column * SQUARE_SIZE, row * SQUARE_SIZE))
            # highlight moves from square
            surface.fill(pygame.Color("green"))
            for move in valid_moves:
                if move.start_row == row and move.start_column == column:
                    screen.blit(surface, (move.end_column * SQUARE_SIZE, move.end_row * SQUARE_SIZE))
        
    # highlight last move played
    if last_move is not None:
        # start square of the last move
        start_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE))
        start_surface.set_alpha(100)  # transparency
        start_surface.fill(pygame.Color("yellow"))  # Start square color
        screen.blit(start_surface, (last_move.start_column * SQUARE_SIZE, last_move.start_row * SQUARE_SIZE))
        
        # end square of the last move
        end_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE))
        end_surface.set_alpha(100)  # transparency
        end_surface.fill(pygame.Color("yellow"))  # End square color
        screen.blit(end_surface, (last_move.end_column * SQUARE_SIZE, last_move.end_row * SQUARE_SIZE))

def draw_pieces(screen: pygame.display, board: list[list[str]]) -> None:
    for row in range(DIMENSION):
        for column in range(DIMENSION):
            piece = board[row, column]
            if piece != "..": # Not empty square
                screen.blit(IMAGES[piece], pygame.Rect(column * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

def draw_move_log(screen: pygame.display, game_state: ChessEngine.GameState, font: pygame.font) -> None:
    move_log_rect = pygame.Rect(BOARD_WIDTH, 0, MOVE_LOG_PANEL_WIDTH, MOVE_LOG_PANEL_HEIGHT)
    pygame.draw.rect(screen, pygame.Color("black"), move_log_rect)
    move_log = game_state.move_log
    move_texts = []
    
    for i in range(0, len(move_log), 2):
        move_string = str(i // 2 + 1) + "."  # start with the move number
        move_string += " " + str(move_log[i])  # add white's move
        if i + 1 < len(move_log):  # Ensure black made a move
            move_string += " " + str(move_log[i + 1])  # add black's move
        move_texts.append(move_string)

    # columns and rows
    moves_per_column = 39
    padding = 5
    column_spacing = 200  # space between columns
    text_x = padding
    text_y = padding

    for i in range(len(move_texts)):
        move_text = move_texts[i]
        
        text_object = font.render(move_text, True, pygame.Color("white"))
        text_location = move_log_rect.move(text_x, text_y)
        screen.blit(text_object, text_location)
        
        # update y position for next line
        text_y += text_object.get_height()

        # once 39 moves have been displayed, move to the next column
        if (i + 1) % moves_per_column == 0:
            text_x += column_spacing  # move to next column
            text_y = padding  # reset Y position for new column

def draw_game_state(screen: pygame.display, game_state: ChessEngine.GameState, valid_moves: list[ChessEngine.Move], square_selected: tuple[int, int], move_log_font: pygame.font, last_move: ChessEngine.Move = None) -> None:
    draw_board(screen)
    highlight_squares(screen, game_state, valid_moves, square_selected, last_move)
    draw_pieces(screen, game_state.board)
    draw_move_log(screen, game_state, move_log_font)

def animate_move(move: ChessEngine.Move, screen: pygame.display, board: list[list[str]], clock: pygame.time.Clock) -> None:
    global colors
    delta_row = move.end_row - move.start_row
    delta_column = move.end_column - move.start_column
    animation_duration = 0.3  # animation duration in seconds
    frames_per_second = 60  # frame rate
    frame_count = int(animation_duration * frames_per_second)  # number of frames for the animation (0.5 seconds)
    
    for frame in range(frame_count + 1):
        # calculate the current position based on the frame
        row = move.start_row + delta_row * frame / frame_count
        column = move.start_column + delta_column * frame / frame_count
        
        # draw the board and pieces
        draw_board(screen)
        draw_pieces(screen, board)
        
        # draw the end square
        color = colors[(move.end_row + move.end_column) % 2]
        end_square = pygame.Rect(move.end_column * SQUARE_SIZE, move.end_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        pygame.draw.rect(screen, color, end_square)
        
        # if there's a captured piece, draw it
        if move.piece_captured != "..":
            screen.blit(IMAGES[move.piece_captured], end_square)
        
        # draw the moving piece at the calculated position
        screen.blit(IMAGES[move.piece_moved], pygame.Rect(column * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        
        # update the display and control the frame rate
        pygame.display.flip()
        clock.tick(frames_per_second)  # ensure the animation runs at 60 FPS

def play_sound(move: ChessEngine.Move) -> None:
    if move.is_check:
        SOUNDS["check"].play()

    elif move.is_pawn_promotion:
        SOUNDS["promote"].play()

    elif move.is_castle_move:
        SOUNDS["castle"].play()
    
    elif move.is_capture:
        SOUNDS["capture"].play()

    else:
        SOUNDS["move"].play()

def main_menu() -> None:
    # Initialize the main menu window
    root = tk.Tk()
    root.title("PyChess Menu")
    x, y = (1400, 500)
    root.geometry(f"800x300+{x}+{y}")  # Set a fixed window size
    root.resizable(False, False)  # Prevent resizing

    # Configure grid layout for centering
    root.grid_rowconfigure(0, weight=1)  # Top spacing
    root.grid_rowconfigure(2, weight=1)  # Bottom spacing
    root.grid_columnconfigure(0, weight=1)  # Left spacing
    root.grid_columnconfigure(4, weight=1)  # Right spacing

    # Variables to store player types
    result = {"player1": None, "player2": None}

    # Image paths
    image_paths = {
        "player_vs_player": ("assets/images/wK.png", "assets/images/bK.png"),
        "player_vs_ai": ("assets/images/wK.png", "assets/images/bQ.png"),
        "ai_vs_ai": ("assets/images/wQ.png", "assets/images/bQ.png"),
    }

    def clear_menu():
        for widget in root.winfo_children():
            widget.destroy()

    # Load and resize images
    def load_image(path, size=(80, 80)):
        img = Image.open(path)
        img = img.convert("RGBA").filter(ImageFilter.SMOOTH_MORE).resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    images = {key: [load_image(path) for path in paths] for key, paths in image_paths.items()}

    # Main menu actions
    def player_vs_player():
        result["player1"] = True
        result["player2"] = True
        root.destroy()  # Close the window

    def ai_vs_ai():
        result["player1"] = False
        result["player2"] = False
        root.destroy()  # Close the window

    def player_vs_ai():
        def set_player_choice(is_white, is_black):
            result["player1"] = is_white
            result["player2"] = is_black
            root.destroy()

        clear_menu()
        
        # Add label asking player choice
        tk.Label(root, text="Do you want to play as White or Black?", font=("Jetbrains Mono", 14)).grid(row=0, column=1, columnspan=2, pady=20)

        # Add images for the white and black kings
        tk.Label(root, image=images["player_vs_ai"][0]).grid(row=1, column=1)  # White King image above White button
        tk.Label(root, image=images["player_vs_player"][1]).grid(row=1, column=2)  # Black King image above Black button

        # Add buttons for White and Black choices
        tk.Button(root, text="White", command=lambda: set_player_choice(True, False), width=10).grid(row=2, column=1, padx=10)
        tk.Button(root, text="Black", command=lambda: set_player_choice(False, True), width=10).grid(row=2, column=2, padx=10)

    # Add title label
    tk.Label(root, text="Choose Game Mode", font=("Jetbrain Mono", 16, "bold")).grid(row=0, column=1, columnspan=3, pady=10)

    # Add buttons with images
    def add_button_with_images(row, column, button_text, images, command):
        frame = tk.Frame(root)
        frame.grid(row=row, column=column, padx=20)

        # Add images side by side
        tk.Label(frame, image=images[0]).grid(row=0, column=0, padx=5)
        tk.Label(frame, image=images[1]).grid(row=0, column=1, padx=5)

        # Add button below the images
        tk.Button(frame, text=button_text, command=command, width=15).grid(row=1, columnspan=2, pady=10)

    add_button_with_images(1, 1, "Player vs Player", images["player_vs_player"], player_vs_player)
    add_button_with_images(1, 2, "Player vs AI", images["player_vs_ai"], player_vs_ai)
    add_button_with_images(1, 3, "AI vs AI", images["ai_vs_ai"], ai_vs_ai)

    # Run the tkinter main loop
    root.mainloop()

    # Return the selected result
    return result["player1"], result["player2"]

def main() -> None:
    player1, player2 = main_menu()

    pygame.mixer.init()
    load_sounds()
    SOUNDS["silence"].play()
    time.sleep(0.5)

    pygame.init()
    load_images()

    screen = pygame.display.set_mode((BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH, BOARD_HEIGHT))
    pygame.display.set_caption("PyChess: The Greatest Kinda Okay Python Chess Engine")
    move_log_font = pygame.font.SysFont("Jetbrains Mono", 19, False, False)
    clock = pygame.time.Clock()
    screen.fill(pygame.Color("white"))
    game_state = ChessEngine.GameState()
    valid_moves = game_state.get_valid_moves()
    move_made = False # flag var for when a move is made
    animate = False # flag var for when to animate
    running = True
    square_selected = () # keep track of last click of user (tuple: (row, column))
    player_clicks = [] # keep track of clicks user made (list of up to two tuples: [(r1, c1), (r2, c2)])
    is_game_over = False
    chess_ai = ChessBot.NegamaxBot()
    last_move = None
    ai_thinking = False
    move_finder_process = None
    move_undone = False

    
    SOUNDS["game_start"].play()

    while running:
        is_human_turn = (game_state.white_to_move and player1) or (not game_state.white_to_move and player2)
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            # mouse handler
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if not is_game_over:
                    location = pygame.mouse.get_pos() # (x, y) position of mouse
                    column = location[0] // SQUARE_SIZE
                    row = location[1] // SQUARE_SIZE
                    if square_selected == (row, column) or column >= 8: # user clicked same square twice (undo) or user clicked move log
                        square_selected = () # deselect
                        player_clicks = [] # clear player clicks
                    else:
                        square_selected = (row, column)
                        player_clicks.append(square_selected) # append both 1st and 2nd clicks
                    if len(player_clicks) == 2 and is_human_turn:  # after 2nd click
                        if game_state.board[player_clicks[0][0], player_clicks[0][1]] == "..":
                            square_selected = ()
                            player_clicks = []
                        else:
                            move = ChessEngine.Move(player_clicks[0], player_clicks[1], game_state.board)
                            for valid_move in valid_moves:
                                if move == valid_move:
                                    game_state.make_move(valid_move)
                                    last_move = valid_move
                                    move_made = True
                                    square_selected = ()
                                    player_clicks = []
                                    animate = True
                            if not move_made:
                                player_clicks = [square_selected]

            # key handler
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_u: # undo when key "u" is pressed
                    if game_state.checkmate or game_state.stalemate or game_state.check_for_insufficient_material() or game_state.check_for_threefold_repetition():
                        is_game_over = False
                    game_state.undo_move()
                    last_move = None
                    move_made = True
                    animate = False
                    is_game_over = False

                    if ai_thinking:
                        move_finder_process.terminate()
                        ai_thinking = False

                    move_undone = True

                if event.key == pygame.K_r: # reset board when key "r" pressed
                    game_state = ChessEngine.GameState()
                    valid_moves = game_state.get_valid_moves()
                    square_selected = ()
                    player_clicks = []
                    move_made = False
                    last_move = None
                    is_game_over = False
                    animate = False

                    if ai_thinking:
                        move_finder_process.terminate()
                        ai_thinking = False

                    move_undone = True

        # ai move finder
        if not is_game_over and not is_human_turn and not move_undone:
            if not ai_thinking:
                ai_thinking = True
                print("Thinking Of Move...")
                return_queue = Queue() # used to pass data between threads
                move_finder_process = Process(target=chess_ai.find_best_move, args=(game_state, valid_moves, return_queue))
                move_finder_process.start() # calls find_best_move(game_state, valid_moves, return_queue)
            
            if not move_finder_process.is_alive():
                print("Finished Thinking")
                ai_move = return_queue.get()
                if ai_move is None:
                    ai_move = ChessBot.RandomBot().find_random_move(valid_moves)
                    ai_move.promotion_choice = ChessBot.RandomBot().choose_random_promotion_piece()
                    print("No Moves Found")
                game_state.make_move(ai_move, promotion_choice=ai_move.promotion_choice)
                last_move = ai_move
                move_made = True
                is_human_turn = True
                ai_thinking = False
                animate = True

        if move_made:
            if animate:
                play_sound(game_state.move_log[-1])
                animate_move(game_state.move_log[-1], screen, game_state.board, clock)
            valid_moves = game_state.get_valid_moves()
            move_made = False
            animate = False
            move_undone = False

        # update screen before checkmate/stalemate handling
        draw_game_state(screen, game_state, valid_moves, square_selected, move_log_font, last_move)
        pygame.display.flip()

        if not is_game_over:
            if game_state.check_for_insufficient_material():
                is_game_over = True
                SOUNDS["game_end"].play()
                ChessEngine.DrawWindow("By Insufficient Material").show()
            
            elif game_state.check_for_threefold_repetition():
                is_game_over = True
                SOUNDS["game_end"].play()
                ChessEngine.DrawWindow("By Threefold Repetition").show()
            
            elif game_state.check_for_fifty_move_rule():
                is_game_over = True
                SOUNDS["game_end"].play()
                ChessEngine.DrawWindow("By 50-Move Rule").show()
            
            elif game_state.checkmate or game_state.stalemate:
                is_game_over = True
                SOUNDS["game_end"].play()
                if game_state.checkmate:
                    if game_state.move_log:
                        last_move = game_state.move_log[-1]
                        last_move_str = str(last_move)
                        edited_last_move = last_move_str[:-1] + "#"
                        game_state.move_log[-1] = edited_last_move
                    
                    # render the board before opening the checkmate window
                    draw_game_state(screen, game_state, valid_moves, square_selected, move_log_font, last_move)
                    pygame.display.flip()
                    pygame.time.delay(50)  # allow the board update to be visible
                    
                    winner_color = "w" if not game_state.white_to_move else "b"
                    ChessEngine.CheckmateWindow(winner_color).show()
                
                elif game_state.stalemate:
                    SOUNDS["game_end"].play()
                    ChessEngine.StalemateWindow().show()

        clock.tick(MAX_FPS)

if __name__ == "__main__":
    main()