from pst import *
import random

class ZobristHashing:
    def __init__(self):
        self.zobrist_table = self.init_zobrist()
        self.transposition_table = {}

    def init_zobrist(self):
        zobrist_table = [[0 for _ in range(12)] for _ in range(64)]  # 64 squares × 12 piece types
        for square in range(64):
            for piece in range(12):
                zobrist_table[square][piece] = hash((square, piece)) & ((1 << 64) - 1) # add piece bitstring
        zobrist_table.append(hash("black_to_move") & ((1 << 64) - 1))  # add "black_to_move" bitstring
        return zobrist_table

    def compute_hash(self, board, is_black_to_move):
        h = 0
        if is_black_to_move:
            h ^= self.zobrist_table[-1]  # XOR the "black to move" bitstring

        for row in range(8):  # loop over rows
            for col in range(8):  # loop over columns
                piece = board[row, col]  # get the piece on this square
                if piece != "..":  # if the square is not empty
                    piece_index = self.get_piece_index(piece)  # map piece to its index
                    square_index = row * 8 + col  # flatten row and column to a square index
                    h ^= self.zobrist_table[square_index][piece_index]  # XOR the square/piece random value

        return h

    def get_piece_index(self, piece):
        piece_map = {
            "wP": 0, "wR": 1, "wN": 2, "wB": 3, "wQ": 4, "wK": 5,
            "bP": 6, "bR": 7, "bN": 8, "bB": 9, "bQ": 10, "bK": 11
        }
        return piece_map.get(piece, -1)


    def lookup_transposition_table(self, zobrist_hash, depth, alpha, beta):
        entry = self.transposition_table.get(zobrist_hash)
        if entry and entry['depth'] >= depth:
            if entry['flag'] == 'exact':
                return entry['value']
            elif entry['flag'] == 'lowerbound' and entry['value'] > alpha:
                alpha = entry['value']
            elif entry['flag'] == 'upperbound' and entry['value'] < beta:
                beta = entry['value']
            if alpha >= beta:
                return entry['value']
        return None

    def store_in_transposition_table(self, zobrist_hash, depth, value, flag):
        self.transposition_table[zobrist_hash] = {
            'depth': depth,
            'value': value,
            'flag': flag
        }

class RandomBot:
    def __init__(self): 
        pass

    def find_random_move(self, valid_moves):
        return valid_moves[random.randint(0, len(valid_moves) - 1)]

    def choose_random_promotion_piece(self):
        return random.choice(["Q", "R", "B", "N"])

class GreedyBot:
    def __init__(self):
        self.piece_score = {"K": 1000, "Q": 9, "R": 5, "B": 3, "N": 3, "P": 1}
        self.CHECKMATE_SCORE = 1000
        self.STALEMATE_SCORE = 0

    def score_material(self, board):
        score = 0
        for row in board:
            for square in row:
                if square[0] == "w":
                    score += self.piece_score[square[1]]
                elif square[0] == "b":
                    score -= self.piece_score[square[1]]
        return score
    
    def find_best_move(self, game_state, valid_moves):
        turn_multiplier = 1 if game_state.white_to_move else -1
        opponent_min_max_score = self.CHECKMATE_SCORE
        best_player_move = None
        random.shuffle(valid_moves)
        for player_move in valid_moves:
            game_state.make_move(player_move, is_ai_move=True)
            opponent_moves = game_state.get_valid_moves()
            if game_state.stalemate:
                opponent_max_score = self.STALEMATE_SCORE

            elif game_state.checkmate:
                opponent_max_score = -self.CHECKMATE_SCORE

            else:
                opponent_max_score = -self.CHECKMATE_SCORE
                for opponent_move in opponent_moves:
                    game_state.make_move(opponent_move, is_ai_move=True)
                    game_state.get_valid_moves()
                    if game_state.checkmate:
                        score = self.CHECKMATE_SCORE

                    elif game_state.stalemate:
                        score = self.STALEMATE_SCORE

                    else:
                        score = -turn_multiplier * self.score_material(game_state.board)

                    if score > opponent_max_score:
                        opponent_max_score = score
                    game_state.undo_move()

            if opponent_max_score < opponent_min_max_score:
                opponent_min_max_score = opponent_max_score
                best_player_move = player_move
            game_state.undo_move()

        return best_player_move

class MinimaxBot:
    def __init__(self):
        self.max_depth = 2
        self.piece_score = {"K": 1000, "Q": 9, "R": 5, "B": 3, "N": 3, "P": 1}
        self.CHECKMATE_SCORE = 1000
        self.STALEMATE_SCORE = 0
    
    def score_board(self, game_state):
        if game_state.checkmate:
            if game_state.white_to_move:
                return -self.CHECKMATE_SCORE
            else:
                return self.CHECKMATE_SCORE
            
        elif game_state.stalemate:
            return self.STALEMATE_SCORE

        score = 0
        for row in game_state.board:
            for square in row:
                if square[0] == "w":
                    score += self.piece_score[square[1]]
                elif square[0] == "b":
                    score -= self.piece_score[square[1]]
        return score

    def find_best_move(self, game_state, valid_moves):
        global next_move
        next_move = None
        self.minimax(game_state, valid_moves, self.max_depth, game_state.white_to_move)
        return next_move

    def minimax(self, game_state, valid_moves, depth, maximizing):
        global next_move
        if depth == 0:
            return self.score_board(game_state)
        
        random.shuffle(valid_moves)
        
        if maximizing:
            max_score = -self.CHECKMATE_SCORE
            for move in valid_moves:
                game_state.make_move(move, is_ai_move=True)
                next_moves = game_state.get_valid_moves()
                score = self.minimax(game_state, next_moves, depth - 1, False)
                if score > max_score:
                    max_score = score
                    if depth == self.max_depth:
                        next_move = move
                game_state.undo_move()

            return max_score
        
        else: # minimizing
            min_score = self.CHECKMATE_SCORE
            for move in valid_moves:
                game_state.make_move(move)
                next_moves = game_state.get_valid_moves()
                score = self.minimax(game_state, next_moves, depth - 1, True)
                if score < min_score:
                    min_score = score
                    if depth == self.max_depth:
                        next_move = move
                game_state.undo_move()
            
            return min_score

class NegamaxBot:
    def __init__(self):
        # psts
        self.white_pawn_pst = white_pawn_pst
        self.black_pawn_pst = black_pawn_pst
        self.white_knight_pst = white_knight_pst
        self.black_knight_pst = black_knight_pst
        self.white_bishop_pst = white_bishop_pst
        self.black_bishop_pst = black_bishop_pst
        self.white_rook_pst = white_rook_pst
        self.black_rook_pst = black_rook_pst
        self.white_queen_pst = white_queen_pst
        self.black_queen_pst = black_queen_pst

        self.max_depth = 3
        self.piece_score = {"K": 1000, "Q": 9, "R": 5, "B": 3.1, "N": 2.9, "P": 1}
        self.pst_mapping = {
            "wP": self.white_pawn_pst, 
            "bP": self.black_pawn_pst, 
            "wN": self.white_knight_pst, 
            "bN": self.black_knight_pst, 
            "wB": self.white_bishop_pst, 
            "bB": self.black_bishop_pst, 
            "wR": self.white_rook_pst, 
            "bR": self.black_rook_pst, 
            "wQ": self.white_queen_pst, 
            "bQ": self.black_queen_pst
        }
        self.next_move = None
        self.branch_counter = 0
        self.zobrist_hashing = ZobristHashing()
        self.CHECKMATE_SCORE = 1000

    def score_board(self, game_state):
        if game_state.checkmate:
            return -self.CHECKMATE_SCORE if game_state.white_to_move else self.CHECKMATE_SCORE

        elif game_state.stalemate or game_state.check_for_insufficient_material() or game_state.check_for_threefold_repetition() or game_state.check_for_fifty_move_rule():
            return -self.CHECKMATE_SCORE if game_state.white_to_move else self.CHECKMATE_SCORE # discourage draws

        score = 0

        for row in range(game_state.board.shape[0]):
            for column in range(game_state.board.shape[1]):
                square = game_state.board[row, column]
                if square != "..":
                    piece = square[1]
                    if piece != "K":
                        piece_position_score = self.pst_mapping[square][row, column]
                        
                        if square[0] == "w":  # White piece
                            score += self.piece_score[piece] + piece_position_score * 0.35
                        elif square[0] == "b":  # Black piece
                            score -= self.piece_score[piece] + piece_position_score * 0.35
        return score

    def order_moves(self, valid_moves):
        def move_score(move):
            score = 0

            if move.is_check:
                score += 10

            if move.is_capture:
                captured_value = self.piece_score.get(move.piece_captured[1], 0)
                attacker_value = self.piece_score.get(move.piece_moved[1], 1)
                score += captured_value * 5 - attacker_value

            if move.is_castle_move:
                score += 15

            if move.is_pawn_promotion:
                score += 20

            if move.piece_moved[1] == "P" and not move.is_capture:
                score -= 3

            return score

        valid_moves.sort(key=move_score, reverse=True)

    def find_best_move(self, game_state, valid_moves, return_queue):
        # self.negamax(game_state, valid_moves, self.max_depth, 1 if game_state.white_to_move else -1)
        self.negamax_alpha_beta_pruning(game_state, valid_moves, self.max_depth, -self.CHECKMATE_SCORE, self.CHECKMATE_SCORE, 1 if game_state.white_to_move else -1)
        print(f"Branches Evaluated: {self.branch_counter}")
        return_queue.put(self.next_move)

    def negamax(self, game_state, valid_moves, depth, turn_multiplier):
        self.branch_counter += 1

        if depth == 0:
            return turn_multiplier * self.score_board(game_state)
        
        random.shuffle(valid_moves)

        max_score = -self.CHECKMATE_SCORE
        for move in valid_moves:
            game_state.make_move(move, is_ai_move=True)
            next_moves = game_state.get_valid_moves()
            score = -self.negamax(game_state, next_moves, depth - 1, -turn_multiplier)
            if score > max_score:
                max_score = score
                if depth == self.max_depth:
                    self.next_move = move
            game_state.undo_move()
        
        return max_score
    
    def find_best_promotion_piece(self, game_state, move):
        promotion_piece = "Q"  # Default promotion to queen
        game_state.make_move(move, promotion_choice=promotion_piece)
        is_checkmate = game_state.checkmate
        game_state.undo_move()

        if not is_checkmate:
            for piece in ["R", "B", "N"]:
                game_state.make_move(move, promotion_choice=piece)
                is_checkmate = game_state.checkmate
                game_state.undo_move()
                if is_checkmate:
                    promotion_piece = piece
                    break

        return promotion_piece

    def negamax_alpha_beta_pruning(self, game_state, valid_moves, depth, alpha, beta, turn_multiplier):
        self.branch_counter += 1

        # compute zobrist hash for current board state
        board_hash = self.zobrist_hashing.compute_hash(game_state.board, not game_state.white_to_move)
        cached_score = self.zobrist_hashing.lookup_transposition_table(board_hash, depth, alpha, beta)
        if cached_score is not None:
            return cached_score # return cached value if found

        if depth == 0: # TODO: add quiescence search mabye?
            score =  turn_multiplier * self.score_board(game_state)
            self.zobrist_hashing.store_in_transposition_table(board_hash, depth, score, "exact")
            return score
        
        self.order_moves(valid_moves)

        max_score = -self.CHECKMATE_SCORE
        is_first_move = True
        reduction_factor = 1 # reduction factor for LMR
        move_log_length = len(game_state.move_log)

        for move_idx, move in enumerate(valid_moves):
            # handle pawn promotions
            if move.is_pawn_promotion:
                promotion_piece = self.find_best_promotion_piece(game_state, move)
                game_state.make_move(move, promotion_choice=promotion_piece)
            else:
                game_state.make_move(move)

            next_moves = game_state.get_valid_moves()

            # check if LMR is applicable
            apply_lmr = (
                depth >= 3 and  # don't reduce for shallow searches
                not move.is_capture and
                not move.is_check and
                not move.is_pawn_promotion and  # don't reduce for promotions
                not is_first_move and  # don't reduce first move
                move_idx >= 4 and  # apply LMR only to moves further back in the list
                move_log_length > 12  # apply LMR only after 6 full moves (12 plies)
            )

            # get piece values for pruning consideration
            if move.is_capture:
                capturing_piece_value = self.piece_score[move.piece_moved[1]]
                captured_piece_value = self.piece_score[move.piece_captured[1]]

            if move.is_capture and captured_piece_value >= capturing_piece_value:
                # do not prune if captured piece value is equal or greater than the capturing piece
                apply_lmr = False

            if apply_lmr:
                reduced_depth = depth - reduction_factor
                score = -self.negamax_alpha_beta_pruning(game_state, next_moves, reduced_depth, -alpha - 1, -alpha, -turn_multiplier)
                if score > alpha:  # search with full depth if reduced-depth search seems good
                    score = -self.negamax_alpha_beta_pruning(game_state, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)
            else:
                score = -self.negamax_alpha_beta_pruning(game_state, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)

            # Undo move
            game_state.undo_move()

            if score > max_score:
                max_score = score
                if depth == self.max_depth:
                    self.next_move = move
                    if move.is_pawn_promotion:
                        self.next_move.promotion_choice = promotion_piece  # store the chosen promotion piece

            if max_score > alpha:
                alpha = max_score

            # alpha-beta pruning
            if alpha >= beta:
                # avoid pruning if captured piece value is equal or greater than capturing piece
                if move.is_capture and captured_piece_value >= capturing_piece_value:
                    continue
                break

        is_first_move = False  # update after processing the first move
        
        # store result in transposition table
        flag = "exact" if alpha >= beta else ("lowerbound" if max_score > alpha else "upperbound")
        self.zobrist_hashing.store_in_transposition_table(board_hash, depth, max_score, flag)

        return max_score