import numpy as np
import copy
import tkinter as tk
from PIL import Image, ImageTk, ImageFilter

class GameState:
    def __init__(self):
        self.board = np.array([
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bP", "bP", "bP", "bP", "bP", "bP", "bP", "bP"],
            ["..", "..", "..", "..", "..", "..", "..", ".."],
            ["..", "..", "..", "..", "..", "..", "..", ".."],
            ["..", "..", "..", "..", "..", "..", "..", ".."],
            ["..", "..", "..", "..", "..", "..", "..", ".."],
            ["wP", "wP", "wP", "wP", "wP", "wP", "wP", "wP"],
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]
        ], dtype="<U2")

        self.move_log = []
        self.ply_count = 0
        self.white_to_move = True
        self.white_king_location = (7, 4)
        self.black_king_location = (0, 4)
        self.in_check = False
        self.pins = []
        self.checks = []
        self.checkmate = False
        self.stalemate = False
        self.enpassant_possible = () # coords for square where enpassant possible
        self.enpassant_possible_log = [self.enpassant_possible]
        self.current_castling_rights = CastleRights(True, True, True, True)
        self.castle_rights_log = [CastleRights(self.current_castling_rights.white_kingside, self.current_castling_rights.black_kingside, 
                                               self.current_castling_rights.white_queenside, self.current_castling_rights.black_queenside)]

    def show_promotion_window(self, color):
        root = tk.Tk()
        window = PromotionWindow(root, color)
        root.mainloop()
        return window.selected_piece if window.selected_piece else "Q"

    def make_move(self, move, promotion_choice=None):
        self.board[move.start_row, move.start_column] = ".."
        self.board[move.end_row, move.end_column] = move.piece_moved
        self.move_log.append(move)  # log move to be able to undo later (or show move history)
        self.white_to_move = not self.white_to_move  # switch turns
        # update king's position
        if move.piece_moved == "wK":
            self.white_king_location = (move.end_row, move.end_column)
        elif move.piece_moved == "bK":
            self.black_king_location = (move.end_row, move.end_column)

        # pawn promotion
        if move.is_pawn_promotion:
            color = move.piece_moved[0]

            if promotion_choice:  # Use the promotion piece passed by the AI
                promoted_piece = promotion_choice
            else:
                promoted_piece = self.show_promotion_window(color)  # Show promotion window only if no choice is passed
            self.board[move.end_row, move.end_column] = color + promoted_piece
            move.promotion_choice = promoted_piece
        
        # enpassant
        if move.is_enpassant_move:
            self.board[move.start_row, move.end_column] = ".."  # capturing the pawn
        
        # update enpassant_possible
        if move.piece_moved[1] == "P" and abs(move.start_row - move.end_row) == 2:  # only on 2 square pawn advance
            self.enpassant_possible = ((move.start_row + move.end_row) // 2, move.start_column)
        else:
            self.enpassant_possible = ()

        # castle move
        if move.is_castle_move:
            if move.end_column - move.start_column == 2:  # kingside castle
                self.board[move.end_row, move.end_column - 1] = self.board[move.end_row, move.end_column + 1]  # copies rook into new square
                self.board[move.end_row, move.end_column + 1] = ".."  # erase old rook
            else:  # queenside castle
                self.board[move.end_row, move.end_column + 1] = self.board[move.end_row, move.end_column - 2]  # copies rook into new square
                self.board[move.end_row, move.end_column - 2] = ".."  # erase old rook

        self.enpassant_possible_log.append(self.enpassant_possible)

        # update castling rights
        self.update_castle_rights(move)
        self.castle_rights_log.append(CastleRights(self.current_castling_rights.white_kingside, self.current_castling_rights.black_kingside, 
                                                self.current_castling_rights.white_queenside, self.current_castling_rights.black_queenside))

        # check if the move is a pawn move or a capture (for 50 move rule)
        if move.piece_moved[1] == "P" or move.is_capture:
            self.ply_count = 0  # reset on pawn move or capture
        else:
            self.ply_count += 1  # increment otherwise

    def undo_move(self):
        if len(self.move_log) != 0:  # make sure there is a move to undo
            last_move = self.move_log.pop()

            # Undo the move using numpy array slicing
            self.board[last_move.start_row, last_move.start_column] = last_move.piece_moved
            self.board[last_move.end_row, last_move.end_column] = last_move.piece_captured
            self.white_to_move = not self.white_to_move  # switch turns after undo

            # Update king's position
            if last_move.piece_moved == "wK":
                self.white_king_location = (last_move.start_row, last_move.start_column)
            elif last_move.piece_moved == "bK":
                self.black_king_location = (last_move.start_row, last_move.start_column)

            # Undo enpassant move
            if last_move.is_enpassant_move:
                self.board[last_move.end_row, last_move.end_column] = ".."  # leave landing square blank
                self.board[last_move.start_row, last_move.end_column] = last_move.piece_captured

            self.enpassant_possible_log.pop()
            self.enpassant_possible = copy.deepcopy(self.enpassant_possible_log[-1])

            # Undo castling rights
            self.castle_rights_log.pop()  # get rid of new castle rights from move we are undoing
            self.current_castling_rights = copy.deepcopy(self.castle_rights_log[-1])  # set to last value

            # Undo castle move
            if last_move.is_castle_move:
                if last_move.end_column - last_move.start_column == 2:  # kingside castle
                    self.board[last_move.end_row, last_move.end_column + 1] = self.board[last_move.end_row, last_move.end_column - 1]
                    self.board[last_move.end_row, last_move.end_column - 1] = ".."
                else:  # queenside castle
                    self.board[last_move.end_row, last_move.end_column - 2] = self.board[last_move.end_row, last_move.end_column + 1]
                    self.board[last_move.end_row, last_move.end_column + 1] = ".."

            self.checkmate = False
            self.stalemate = False

    def update_castle_rights(self, move):
        if move.piece_moved == "wK":
            self.current_castling_rights.white_kingside = False
            self.current_castling_rights.white_queenside = False

        elif move.piece_moved == "bK":
            self.current_castling_rights.black_kingside = False
            self.current_castling_rights.black_queenside = False

        elif move.piece_moved == "wR":
            if move.start_row == 7:
                if move.start_column == 0: # left rook
                    self.current_castling_rights.white_queenside = False
                elif move.start_column == 7: # right rook
                    self.current_castling_rights.white_kingside = False

        elif move.piece_moved == "bR":
            if move.start_row == 0:
                if move.start_column == 0: # left rook
                    self.current_castling_rights.black_queenside = False
                elif move.start_column == 7: # right rook
                    self.current_castling_rights.black_kingside = False
        
        # if a rook is captured
        if move.piece_captured == 'wR':
            if move.end_row == 7:
                if move.end_column == 0:
                    self.current_castling_rights.white_queenside = False
                elif move.end_column == 7:
                    self.current_castling_rights.white_kingside = False
        elif move.piece_captured == 'bR':
            if move.end_row == 0:
                if move.end_column == 0:
                    self.current_castling_rights.black_queenside = False
                elif move.end_column == 7:
                    self.current_castling_rights.black_kingside = False

    def get_pawn_moves(self, row, column, moves):
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == column:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break

        if self.white_to_move:  # white pawn moves
            king_row, king_column = self.white_king_location
            if row - 1 >= 0:
                if self.board[row - 1, column] == "..":  # 1 square pawn advance
                    if not piece_pinned or pin_direction == (-1, 0):
                        if row - 1 == 0:  # Promotion
                            moves.append(Move((row, column), (row - 1, column), self.board))
                        else:
                            moves.append(Move((row, column), (row - 1, column), self.board))
                        if row == 6 and self.board[row - 2, column] == "..":  # 2 square pawn advance
                            moves.append(Move((row, column), (row - 2, column), self.board))

                if column - 1 >= 0:  # leftward capture
                    if not piece_pinned or pin_direction == (-1, -1):
                        if self.board[row - 1, column - 1][0] == "b":  # capture black piece
                            if row - 1 == 0:  # Promotion
                                moves.append(Move((row, column), (row - 1, column - 1), self.board))
                            else:
                                moves.append(Move((row, column), (row - 1, column - 1), self.board))

                        if (row - 1, column - 1) == self.enpassant_possible:
                            is_attacking_piece = is_blocking_piece = False
                            if king_row == row:
                                if king_column < column:  # king is left of pawn
                                    inside_range = range(king_column + 1, column - 1)
                                    outside_range = range(column + 1, 8)
                                else:  # king is right of pawn
                                    inside_range = range(king_column - 1, column, -1)
                                    outside_range = range(column - 2, -1, -1)
                                for i in inside_range:
                                    if self.board[row, i] != "..":  # some other piece beside enpassant pawn blocks
                                        is_blocking_piece = True
                                for i in outside_range:
                                    square = self.board[row, i]
                                    if square[0] == "b" and (square[1] == "R" or square[1] == "Q"):  # attacking piece
                                        is_attacking_piece = True
                                    elif square != "..":
                                        is_blocking_piece = True

                            if not is_attacking_piece or is_blocking_piece:
                                moves.append(Move((row, column), (row - 1, column - 1), self.board, is_enpassant_move=True))

                if column + 1 <= 7:  # rightward capture
                    if not piece_pinned or pin_direction == (-1, 1):
                        if self.board[row - 1, column + 1][0] == "b":  # capture black piece
                            if row - 1 == 0:  # Promotion
                                moves.append(Move((row, column), (row - 1, column + 1), self.board))
                            else:
                                moves.append(Move((row, column), (row - 1, column + 1), self.board))

                        if (row - 1, column + 1) == self.enpassant_possible:
                            is_attacking_piece = is_blocking_piece = False
                            if king_row == row:
                                if king_column < column:  # king is left of pawn
                                    inside_range = range(king_column + 1, column)
                                    outside_range = range(column + 2, 8)
                                else:  # king is right of pawn
                                    inside_range = range(king_column - 1, column + 1, -1)
                                    outside_range = range(column - 1, -1, -1)
                                for i in inside_range:
                                    if self.board[row, i] != "..":  # some other piece beside enpassant pawn blocks
                                        is_blocking_piece = True
                                for i in outside_range:
                                    square = self.board[row, i]
                                    if square[0] == "b" and (square[1] == "R" or square[1] == "Q"):  # attacking piece
                                        is_attacking_piece = True
                                    elif square != "..":
                                        is_blocking_piece = True

                            if not is_attacking_piece or is_blocking_piece:
                                moves.append(Move((row, column), (row - 1, column + 1), self.board, is_enpassant_move=True))

        else:  # black pawn moves
            king_row, king_column = self.black_king_location
            if row + 1 <= 7:
                if self.board[row + 1, column] == "..":  # 1 square pawn advance
                    if not piece_pinned or pin_direction == (1, 0):
                        if row + 1 == 7:  # Promotion
                            moves.append(Move((row, column), (row + 1, column), self.board))
                        else:
                            moves.append(Move((row, column), (row + 1, column), self.board))

                        if row == 1 and self.board[row + 2, column] == "..":  # 2 square pawn advance
                            moves.append(Move((row, column), (row + 2, column), self.board))

                if column - 1 >= 0:  # leftward capture
                    if not piece_pinned or pin_direction == (1, -1):
                        if self.board[row + 1, column - 1][0] == "w":  # capture white piece
                            if row + 1 == 7:  # Promotion
                                moves.append(Move((row, column), (row + 1, column - 1), self.board))
                            else:
                                moves.append(Move((row, column), (row + 1, column - 1), self.board))

                        if (row + 1, column - 1) == self.enpassant_possible:
                            is_attacking_piece = is_blocking_piece = False
                            if king_row == row:
                                if king_column < column:  # king is left of pawn
                                    inside_range = range(king_column + 1, column - 1)
                                    outside_range = range(column + 1, 8)
                                else:  # king is right of pawn
                                    inside_range = range(king_column - 1, column, -1)
                                    outside_range = range(column - 2, -1, -1)
                                for i in inside_range:
                                    if self.board[row, i] != "..":  # some other piece beside enpassant pawn blocks
                                        is_blocking_piece = True
                                for i in outside_range:
                                    square = self.board[row, i]
                                    if square[0] == "w" and (square[1] == "R" or square[1] == "Q"):  # attacking piece
                                        is_attacking_piece = True
                                    elif square != "..":
                                        is_blocking_piece = True

                            if not is_attacking_piece or is_blocking_piece:
                                moves.append(Move((row, column), (row + 1, column - 1), self.board, is_enpassant_move=True))

                if column + 1 <= 7:  # rightward capture
                    if not piece_pinned or pin_direction == (1, 1):
                        if self.board[row + 1, column + 1][0] == "w":  # capture white piece
                            if row + 1 == 7:  # Promotion
                                moves.append(Move((row, column), (row + 1, column + 1), self.board))
                            else:
                                moves.append(Move((row, column), (row + 1, column + 1), self.board))

                        if (row + 1, column + 1) == self.enpassant_possible:
                            is_attacking_piece = is_blocking_piece = False
                            if king_row == row:
                                if king_column < column:  # king is left of pawn
                                    inside_range = range(king_column + 1, column)
                                    outside_range = range(column + 2, 8)
                                else:  # king is right of pawn
                                    inside_range = range(king_column - 1, column + 1, -1)
                                    outside_range = range(column - 1, -1, -1)
                                for i in inside_range:
                                    if self.board[row, i] != "..":  # some other piece beside enpassant pawn blocks
                                        is_blocking_piece = True
                                for i in outside_range:
                                    square = self.board[row, i]
                                    if square[0] == "w" and (square[1] == "R" or square[1] == "Q"):  # attacking piece
                                        is_attacking_piece = True
                                    elif square != "..":
                                        is_blocking_piece = True

                            if not is_attacking_piece or is_blocking_piece:
                                moves.append(Move((row, column), (row + 1, column + 1), self.board, is_enpassant_move=True))

    def get_rook_moves(self, row, column, moves):
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == column:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                if self.board[row, column][1] != "Q":  # can't remove queen from pin on rook moves, only remove it on bishop moves
                    self.pins.remove(self.pins[i])
                break

        directions = ((-1, 0), (0, -1), (1, 0), (0, 1))
        enemy_color = "b" if self.white_to_move else "w"
        for direction in directions:
            for i in range(1, 8):
                end_row = row + direction[0] * i
                end_column = column + direction[1] * i
                if 0 <= end_row < 8 and 0 <= end_column < 8:  # on the board
                    if not piece_pinned or pin_direction == direction or pin_direction == (-direction[0], -direction[1]):
                        end_piece = self.board[end_row, end_column]
                        if end_piece == "..":  # valid empty space
                            moves.append(Move((row, column), (end_row, end_column), self.board))
                        elif end_piece[0] == enemy_color:  # valid enemy piece
                            moves.append(Move((row, column), (end_row, end_column), self.board))
                            break
                        else:  # invalid same color piece
                            break
                else:  # off the board
                    break

    def get_knight_moves(self, row, column, moves):
        piece_pinned = False
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == column:
                piece_pinned = True
                self.pins.remove(self.pins[i])
                break

        knight_moves = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
        enemy_color = "b" if self.white_to_move else "w"
        for move in knight_moves:
            end_row = row + move[0]
            end_column = column + move[1]
            if 0 <= end_row < 8 and 0 <= end_column < 8:
                if not piece_pinned:
                    end_piece = self.board[end_row, end_column]
                    if end_piece[0] == enemy_color or end_piece[0] == ".": # empty square or enemy piece
                        moves.append(Move((row, column), (end_row, end_column), self.board))

    def get_bishop_moves(self, row, column, moves):
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == column:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break

        directions = ((-1, -1), (-1, 1), (1, -1), (1, 1))
        enemy_color = "b" if self.white_to_move else "w"
        for direction in directions:
            for i in range(1, 8):
                end_row = row + direction[0] * i
                end_column = column + direction[1] * i
                if 0 <= end_row < 8 and 0 <= end_column < 8:  # on the board
                    if not piece_pinned or pin_direction == direction or pin_direction == (-direction[0], -direction[1]):
                        end_piece = self.board[end_row, end_column]
                        if end_piece == "..":  # valid empty space
                            moves.append(Move((row, column), (end_row, end_column), self.board))
                        elif end_piece[0] == enemy_color:  # valid enemy piece
                            moves.append(Move((row, column), (end_row, end_column), self.board))
                            break
                        else:  # invalid same color piece
                            break
                else:  # off the board
                    break

    def get_queen_moves(self, row, column, moves):
        self.get_rook_moves(row, column, moves)
        self.get_bishop_moves(row, column, moves)

    def get_king_moves(self, row, column, moves):
        row_moves = (-1, -1, -1, 0, 0, 1, 1, 1)
        column_moves = (-1, 0, 1, -1, 1, -1, 0, 1)
        enemy_color = "b" if self.white_to_move else "w"

        for i in range(8):  # iterate through all king directions
            end_row = row + row_moves[i]
            end_column = column + column_moves[i]
            if 0 <= end_row < 8 and 0 <= end_column < 8:  # Check board bounds
                end_piece = self.board[end_row, end_column]
                if end_piece[0] == enemy_color or end_piece[0] == ".":  # Enemy or empty square
                    # simulate move
                    if enemy_color == "b":
                        self.white_king_location = (end_row, end_column)
                    else:
                        self.black_king_location = (end_row, end_column)
                    in_check, _, _ = self.check_for_pins_and_checks(end_row, end_column)
                    if not in_check:
                        moves.append(Move((row, column), (end_row, end_column), self.board))
                    # undo simulation
                    if enemy_color == "b":
                        self.white_king_location = (row, column)
                    else:
                        self.black_king_location = (row, column)

        self.get_castle_moves(row, column, moves)

    def get_castle_moves(self, row, column, moves):
        if self.in_check:
            return # cant castle while in check
        if (self.white_to_move and self.current_castling_rights.white_kingside) or (not self.white_to_move and self.current_castling_rights.black_kingside):
            self.get_kingside_castle_moves(row, column, moves)
        if (self.white_to_move and self.current_castling_rights.white_queenside) or (not self.white_to_move and self.current_castling_rights.black_queenside):
            self.get_queenside_castle_moves(row, column, moves)

    def get_kingside_castle_moves(self, row, column, moves):
        if self.board[row, column + 1] == ".." and self.board[row, column + 2] == "..":
            square_in_check1, _, _ = self.check_for_pins_and_checks(row, column + 1)
            square_in_check2, _, _ = self.check_for_pins_and_checks(row, column + 2)
            if not square_in_check1 and not square_in_check2:
                moves.append(Move((row, column), (row, column + 2), self.board, is_castle_move=True))

    def get_queenside_castle_moves(self, row, column, moves):
        if self.board[row, column - 1] == ".." and self.board[row, column - 2] == ".." and self.board[row, column - 3] == "..":
            square_in_check1, _, _ = self.check_for_pins_and_checks(row, column - 1)
            square_in_check2, _, _ = self.check_for_pins_and_checks(row, column - 2)
            if not square_in_check1 and not square_in_check2:
                moves.append(Move((row, column), (row, column - 2), self.board, is_castle_move=True))

    def check_for_pins_and_checks(self, start_row, start_column):
        pins = []  # squares where the allied pinned piece is and the direction pinned from
        checks = []  # squares where the enemy is applying a check
        in_check = False

        if self.white_to_move:
            enemy_color = "b"
            ally_color = "w"
        else:
            enemy_color = "w"
            ally_color = "b"

        # Check all directions for checks and pins
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
        for i in range(len(directions)):
            direction = directions[i]
            possible_pin = ()  # reset possible pins
            for j in range(1, 8):  # Look up to 7 squares away
                end_row = start_row + direction[0] * j
                end_column = start_column + direction[1] * j
                if 0 <= end_row < 8 and 0 <= end_column < 8:  # On the board
                    end_piece = self.board[end_row, end_column]  # Use numpy indexing
                    if end_piece[0] == ally_color and end_piece[1] != "K":
                        if possible_pin == ():  # First allied piece could be pinned
                            possible_pin = (end_row, end_column, direction[0], direction[1])
                        else:  # Second allied piece found, can't be a pin
                            break
                    elif end_piece[0] == enemy_color:
                        piece_type = end_piece[1]
                        # 5 possibilities here in this complex conditional
                        # 1. orthogonally away from king and piece is a rook
                        # 2. diagonally away from king and piece is a bishop
                        # 3. 1 square away and piece is a pawn
                        # 4. any direction and piece is a queen
                        # 5. any direction 1 square away and piece is a king
                        if (0 <= i <= 3 and piece_type == "R") or \
                                (4 <= i <= 7 and piece_type == "B") or \
                                (j == 1 and piece_type == "P" and ((enemy_color == "w" and 6 <= i <= 7) or (enemy_color == "b" and 4 <= i <= 5))) or \
                                (piece_type == "Q") or (j == 1 and piece_type == "K"):
                            if possible_pin == ():  # No piece blocking, so valid check
                                in_check = True
                                checks.append((end_row, end_column, direction[0], direction[1]))
                                break
                            else:  # Piece blocking, so valid pin
                                pins.append(possible_pin)
                                break
                        else:  # Enemy piece not applying a valid check
                            break
                else:  # Off the board
                    break

        # Check for knight attacks
        knight_moves = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
        for move in knight_moves:
            end_row = start_row + move[0]
            end_column = start_column + move[1]
            if 0 <= end_row < 8 and 0 <= end_column < 8:  # On the board
                end_piece = self.board[end_row, end_column]  # Use numpy indexing
                if end_piece[0] == enemy_color and end_piece[1] == "N":  # Enemy knight attacking the square
                    in_check = True
                    checks.append((end_row, end_column, move[0], move[1]))

        return in_check, pins, checks

    def check_for_insufficient_material(self):
        # Get the piece count for each side
        white_pieces = [piece for row in self.board for piece in row if piece[0] == 'w']
        black_pieces = [piece for row in self.board for piece in row if piece[0] == 'b']

        # If either player has a queen, rook, or pawn, it's not insufficient material
        if any(piece[1] in 'QR' for piece in white_pieces + black_pieces):
            return False

        # Count knights and bishops for each side
        white_knights = len([piece for piece in white_pieces if piece[1] == 'N'])
        white_bishops = len([piece for piece in white_pieces if piece[1] == 'B'])
        black_knights = len([piece for piece in black_pieces if piece[1] == 'N'])
        black_bishops = len([piece for piece in black_pieces if piece[1] == 'B'])

        # Handle insufficient material scenarios
        if len(white_pieces) == 1 and len(black_pieces) == 1:  # King vs King
            return True
        if len(white_pieces) == 2 and white_knights == 1 and len(black_pieces) == 1:  # King + Knight vs King
            return True
        if len(white_pieces) == 2 and white_bishops == 1 and len(black_pieces) == 1:  # King + Bishop vs King
            return True
        if len(black_pieces) == 2 and black_knights == 1 and len(white_pieces) == 1:  # King vs King + Knight
            return True
        if len(black_pieces) == 2 and black_bishops == 1 and len(white_pieces) == 1:  # King vs King + Bishop
            return True
        if len(white_pieces) == 3 and white_knights == 2 and len(black_pieces) == 1:  # King + 2 Knights vs King
            return True
        if len(black_pieces) == 3 and black_knights == 2 and len(white_pieces) == 1:  # King vs King + 2 Knights
            return True
        if len(white_pieces) == 2 and len(black_pieces) == 2 and white_bishops == 1 and black_bishops == 1:  # King + Bishop vs King + Bishop
            # Check if bishops are on the same color
            white_bishop_square = [(r, c) for r, row in enumerate(self.board) for c, piece in enumerate(row) if piece == 'wB']
            black_bishop_square = [(r, c) for r, row in enumerate(self.board) for c, piece in enumerate(row) if piece == 'bB']
            if white_bishop_square and black_bishop_square:
                wb_square = white_bishop_square[0]
                bb_square = black_bishop_square[0]
                # Bishops on the same color
                if (wb_square[0] + wb_square[1]) % 2 == (bb_square[0] + bb_square[1]) % 2:
                    return True

        return False

    def check_for_threefold_repetition(self):
        if len(self.move_log) >= 8: # make sure there are at least 4 moves
            last_four_moves = self.move_log[-8:]
            if (last_four_moves[0] == last_four_moves[4] and last_four_moves[2] == last_four_moves[6]) and \
                (last_four_moves[1] == last_four_moves[5] and last_four_moves[3] == last_four_moves[7]):
                return True
        
        return False

    def check_for_fifty_move_rule(self):
        return self.ply_count >= 100

    def get_all_moves(self):
        moves = []
        for row in range(len(self.board)):
            for column in range(len(self.board[row])):
                color = self.board[row, column][0]
                if (color == "w" and self.white_to_move) or (color == 'b' and not self.white_to_move):
                    piece = self.board[row, column][1]
                    match piece:
                        case "P":
                            self.get_pawn_moves(row, column, moves)

                        case "R":
                            self.get_rook_moves(row, column, moves)

                        case "N":
                            self.get_knight_moves(row, column, moves)

                        case "B":
                            self.get_bishop_moves(row, column, moves)

                        case "Q":
                            self.get_queen_moves(row, column, moves)

                        case "K":
                            self.get_king_moves(row, column, moves)
        return moves

    def get_valid_moves(self):
        moves = []
        if self.white_to_move:
            king_row = self.white_king_location[0]
            king_column = self.white_king_location[1]
        else:
            king_row = self.black_king_location[0]
            king_column = self.black_king_location[1]
        
        self.in_check, self.pins, self.checks = self.check_for_pins_and_checks(king_row, king_column)
        
        if self.in_check:
            if len(self.checks) == 1: # only 1 check, block check or move king
                moves = self.get_all_moves()
                # to block a check you must move a piece into one of the squares between the enemy piece nad king
                check = self.checks[0] # check info
                check_row = check[0]
                check_column = check[1]
                piece_checking = self.board[check_row, check_column] # enemy piece causing the check
                valid_squares = [] # squares pieces can move to
                # if knight, must capture knight or move king, other pieces can be blocked
                if piece_checking[1] == "N":
                    valid_squares = [(check_row, check_column)]
                else:
                    for i in range(1, 8):
                        valid_square = (king_row + check[2] * i, king_column + check[3] * i) # check[2] and check[3] are the check directions
                        valid_squares.append(valid_square)
                        if valid_square[0] == check_row and valid_square[1] == check_column: # once you get to the piece end checks
                            break
                # get rid of any moves that don't block check or move king
                for i in range(len(moves) - 1, -1, -1): # go through list of moves backward
                    if moves[i].piece_moved[1] != "K": # move doesn't move king so must block or capture
                        if not (moves[i].end_row, moves[i].end_column) in valid_squares: # move doesn't block check or capture piece
                            moves.remove(moves[i])
            else: # double-check, king must move
                self.get_king_moves(king_row, king_column, moves)
        else: # not in check so all moves are fine
            moves += self.get_all_moves()

        if len(moves) == 0:  # Either checkmate or stalemate
            if self.in_check:
                self.checkmate = True
                self.stalemate = False
            else:
                self.checkmate = False
                self.stalemate = True
        else:
            self.checkmate = False
            self.stalemate = False

        for move in moves:
            move.evaluate_move(self)

        return moves

class CastleRights:
    def __init__(self, white_kingside, black_kingside, white_queenside, black_queenside):
        self.white_kingside = white_kingside
        self.black_kingside = black_kingside
        self.white_queenside = white_queenside
        self.black_queenside = black_queenside

class Move:
    # chess notation mappings
    ranks_to_rows = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}
    rows_to_ranks = {v: k for k, v in ranks_to_rows.items()}
    files_to_columns = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
    columns_to_files = {v: k for k, v in files_to_columns.items()}

    def __init__(self, start_square, end_square, board, is_enpassant_move=False, is_castle_move=False, promotion_choice=None):
        self.start_square = start_square
        self.end_square = end_square
        self.start_row = start_square[0]
        self.start_column = start_square[1]
        self.end_row = end_square[0]
        self.end_column = end_square[1]
        self.piece_moved = board[self.start_row, self.start_column]  # Use numpy array indexing
        self.piece_captured = board[self.end_row, self.end_column]  # Use numpy array indexing
        self.is_pawn_promotion = (self.piece_moved == "wP" and self.end_row == 0) or (self.piece_moved == "bP" and self.end_row == 7)
        self.promotion_choice = promotion_choice
        self.is_enpassant_move = is_enpassant_move
        if self.is_enpassant_move:
            self.piece_captured = "wP" if self.piece_moved == "bP" else "bP"
        # castle move
        self.is_castle_move = is_castle_move
        self.is_capture = self.piece_captured != ".."
        self.is_check = False
        self.move_id = self.start_row * 1000 + self.start_column * 100 + self.end_row * 10 + self.end_column

    def evaluate_move(self, game_state):
        # temporarily make the move
        for piece in ["N", "B", "R", "Q"]:
            game_state.make_move(self, promotion_choice=piece)

            # get the opponent's king location
            king_row, king_column = (
                game_state.white_king_location if game_state.white_to_move else game_state.black_king_location
            )

            # check if the opponent's king is in check
            in_check, _, _ = game_state.check_for_pins_and_checks(king_row, king_column)

            # undo the move
            game_state.undo_move()

            self.is_check = in_check

    # overriding the equals method
    def __eq__(self, value):
        if isinstance(value, Move):
            return self.move_id == value.move_id
        return False

    def get_uci_notation(self):
        return self.get_rank_file(self.start_row, self.start_column) + self.get_rank_file(self.end_row, self.end_column)

    def get_rank_file(self, row, column):
        return self.columns_to_files[column] + self.rows_to_ranks[row]
    
    # overridding the str() function
    def __str__(self):
        # castle move
        if self.is_castle_move:
            return "O-O" if self.end_column == 6 else "O-O-O"

        end_square = self.get_rank_file(self.end_row, self.end_column)
        # pawn moves
        if self.piece_moved[1] == "P":
            move_symbol = ""
            if self.is_pawn_promotion:
                move_symbol += "=" + self.promotion_choice + ("+" if self.is_check else "")
            if self.is_capture:
                return self.columns_to_files[self.start_column] + "x" + end_square + move_symbol + ("+" if self.is_check else "")
            else:
                return end_square + move_symbol
            
        
        # TODO: disambiguation

        move_string = self.piece_moved[1]
        if self.is_capture:
            move_string += "x"

        move_symbol = ""
        if self.is_check:
            move_symbol = "+"

        return move_string + end_square + move_symbol

class PromotionWindow:
    def __init__(self, master, color):
        self.master = master
        self.master.title("Pawn Promotion")
        x, y = (1053, 600)
        self.master.geometry(f"800x200+{x}+{y}")
        self.master.resizable(False, False)
        self.selected_piece = None

        # Color-specific image paths
        piece_images = {
            "w": {
                "N": "wN.png",
                "B": "wB.png",
                "R": "wR.png",
                "Q": "wQ.png"
            },
            "b": {
                "N": "bN.png",
                "B": "bB.png",
                "R": "bR.png",
                "Q": "bQ.png"
            }
        }

        # Create a frame for the piece selection
        frame = tk.Frame(master)
        frame.pack(pady=10)

        # Display options
        for i, (piece, img_path) in enumerate(piece_images[color].items()):
            img = Image.open("assets/images/" + img_path)
            img = img.convert("RGBA").filter(ImageFilter.SMOOTH_MORE)
            img = img.resize((100, 100), Image.LANCZOS)  # Resize with proper resampling
            photo = ImageTk.PhotoImage(img)

            btn = tk.Button(frame, image=photo, command=lambda p=piece: self.select_piece(p))
            btn.image = photo  # Keep a reference to avoid garbage collection
            btn.grid(row=0, column=i, padx=10)

            label = tk.Label(frame, text=piece, font=("Jetbrains Mono", 12))
            label.grid(row=1, column=i)

        # Default selection label
        self.status_label = tk.Label(master, text="Select a piece to promote to.", font=("Jetbrains Mono", 10))
        self.status_label.pack(pady=5)

    def select_piece(self, piece):
        self.selected_piece = piece
        self.master.destroy()  # Close the window

class CheckmateWindow:
    def __init__(self, winner_color):
        self.root = tk.Tk()
        self.root.title("Checkmate!")
        x, y = (1255, 538)
        self.root.geometry(f"400x325+{x}+{y}")
        self.root.resizable(False, False)

        # Display the "Checkmate!" message
        title_label = tk.Label(self.root, text="Checkmate!", font=("Jetbrains Mono", 24, "bold"))
        title_label.pack(pady=10)

        # Display which color wins
        winner_message = f"{'White' if winner_color == 'w' else 'Black'} wins!"
        winner_label = tk.Label(self.root, text=winner_message, font=("Jetbrains Mono", 18))
        winner_label.pack(pady=10)

        # Load and display the king image
        king_image_path = f"assets/images/{winner_color}K.png"
        img = Image.open(king_image_path)
        img = img.resize((100, 100), Image.LANCZOS)
        img = img.convert("RGBA").filter(ImageFilter.SMOOTH_MORE)
        photo = ImageTk.PhotoImage(img)

        image_label = tk.Label(self.root, image=photo)
        image_label.image = photo  # Keep reference to avoid garbage collection
        image_label.pack(pady=10)

        inner_frame = tk.Frame(self.root)
        inner_frame.pack(ipadx=10, ipady=15, fill="both", expand=True)

        # Add an OK button to close the window
        ok_button = tk.Button(inner_frame, height=20, width=5, text="OK", command=self.root.destroy, font=("Jetbrains Mono", 12))
        ok_button.pack(pady=15)

    def show(self):
        self.root.mainloop()

class StalemateWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Stalemate!")
        x, y = (1255, 538)
        self.root.geometry(f"400x325+{x}+{y}")
        self.root.resizable(False, False)

        # Display the "Stalemate" message
        title_label = tk.Label(self.root, text="Stalemate!", font=("Jetbrains Mono", 24, "bold"))
        title_label.pack(pady=10)

        # Display "Draw!"
        draw_label = tk.Label(self.root, text="Draw!", font=("Jetbrains Mono", 18))
        draw_label.pack(pady=10)

        # Load and display the king images
        image_frame = tk.Frame(self.root)
        image_frame.pack(pady=10)

        # Load white king
        white_king_img = Image.open("assets/images/wK.png")
        white_king_img = white_king_img.resize((100, 100), Image.LANCZOS).convert("RGBA").filter(ImageFilter.SMOOTH_MORE)
        white_king_photo = ImageTk.PhotoImage(white_king_img)

        white_king_label = tk.Label(image_frame, image=white_king_photo)
        white_king_label.image = white_king_photo  # Keep reference to avoid garbage collection
        white_king_label.pack(side="left", padx=20)

        # Load black king
        black_king_img = Image.open("assets/images/bK.png")
        black_king_img = black_king_img.resize((100, 100), Image.LANCZOS).convert("RGBA").filter(ImageFilter.SMOOTH_MORE)
        black_king_photo = ImageTk.PhotoImage(black_king_img)

        black_king_label = tk.Label(image_frame, image=black_king_photo)
        black_king_label.image = black_king_photo  # Keep reference to avoid garbage collection
        black_king_label.pack(side="left", padx=20)

        inner_frame = tk.Frame(self.root)
        inner_frame.pack(ipadx=10, ipady=15, fill="both", expand=True)

        # Add an OK button to close the window
        ok_button = tk.Button(inner_frame, height=20, width=5, text="OK", command=self.root.destroy, font=("Jetbrains Mono", 12))
        ok_button.pack(pady=15)

    def show(self):
        self.root.mainloop()

class DrawWindow:
    def __init__(self, reason):
        self.root = tk.Tk()
        self.root.title("Draw!")
        x, y = (1255, 538)
        self.root.geometry(f"400x325+{x}+{y}")
        self.root.resizable(False, False)

        # Display the "Stalemate" message
        title_label = tk.Label(self.root, text="Draw!", font=("Jetbrains Mono", 24, "bold"))
        title_label.pack(pady=10)

        # Display "Draw!"
        draw_label = tk.Label(self.root, text=reason, font=("Jetbrains Mono", 14))
        draw_label.pack(pady=10)

        # Load and display the king images
        image_frame = tk.Frame(self.root)
        image_frame.pack(pady=10)

        # Load white king
        white_king_img = Image.open("assets/images/wK.png")
        white_king_img = white_king_img.resize((100, 100), Image.LANCZOS).convert("RGBA").filter(ImageFilter.SMOOTH_MORE)
        white_king_photo = ImageTk.PhotoImage(white_king_img)

        white_king_label = tk.Label(image_frame, image=white_king_photo)
        white_king_label.image = white_king_photo  # Keep reference to avoid garbage collection
        white_king_label.pack(side="left", padx=20)

        # Load black king
        black_king_img = Image.open("assets/images/bK.png")
        black_king_img = black_king_img.resize((100, 100), Image.LANCZOS).convert("RGBA").filter(ImageFilter.SMOOTH_MORE)
        black_king_photo = ImageTk.PhotoImage(black_king_img)

        black_king_label = tk.Label(image_frame, image=black_king_photo)
        black_king_label.image = black_king_photo  # Keep reference to avoid garbage collection
        black_king_label.pack(side="left", padx=20)

        inner_frame = tk.Frame(self.root)
        inner_frame.pack(ipadx=10, ipady=15, fill="both", expand=True)

        # Add an OK button to close the window
        ok_button = tk.Button(inner_frame, height=20, width=5, text="OK", command=self.root.destroy, font=("Jetbrains Mono", 12))
        ok_button.pack(pady=15)

    def show(self):
        self.root.mainloop()
