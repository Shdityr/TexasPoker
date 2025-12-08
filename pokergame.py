import streamlit as st
from deuces.card import Card
from deuces.deck import Deck
from deuces.evaluator import Evaluator
import random
from itertools import combinations
import time # Simulate AI thinking time


RANKS = '23456789TJQKA'
SUITS = 'shdc'

def create_all_cards():
    all_cards_str = []
    for rank in RANKS:
        for suit in SUITS:
            all_cards_str.append(rank + suit)
    return all_cards_str

ALL_CARDS_STR = create_all_cards()

def format_card_to_emoji(card_str):
    if not card_str or len(card_str) != 2:
        return card_str
    rank = card_str[0].upper()
    suit_char = card_str[1].lower()
    suit_map = {'s': '♠️', 'h': '♥️', 'd': '♦️', 'c': '♣️'}
    rank_map = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}
    display_rank = rank_map.get(rank, rank)
    display_suit = suit_map.get(suit_char, '')
    return f"{display_rank}{display_suit}"

EMOJI_CARDS = [format_card_to_emoji(c) for c in ALL_CARDS_STR]

def convert_emoji_to_deuces_int(emoji_card):
    try:
        index = EMOJI_CARDS.index(emoji_card)
        deuces_str = ALL_CARDS_STR[index]
        return Card.new(deuces_str)
    except ValueError:
        return None

# Assume your calculate_equity function is correctly implemented and includes @st.cache_data
@st.cache_data
def calculate_equity(player_hand_int, board_int, simulations=50000):
    # This is your win rate calculation logic (using Monte Carlo simulation)
    evaluator = Evaluator()
    wins = 0
    ties = 0
    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR] 
    
    # Simplified simulation
    if len(player_hand_int) != 2:
        return 0.0, "N/A"

    for _ in range(simulations):
        known_cards = player_hand_int + board_int
        unknown_pool = [c for c in full_deck_int if c not in known_cards]
        
        num_board = len(board_int)
        needed_for_opp = 2
        needed_for_board = 5 - num_board
        needed_total = needed_for_opp + needed_for_board
        
        if len(unknown_pool) < needed_total:
            continue 

        drawn_cards = random.sample(unknown_pool, needed_total)
        opponent_hand = drawn_cards[:needed_for_opp]
        remaining_board = drawn_cards[needed_for_opp:]
        final_board = board_int + remaining_board

        player_score = evaluator.evaluate(player_hand_int, final_board)
        opponent_score = evaluator.evaluate(opponent_hand, final_board)

        if player_score < opponent_score:
            wins += 1
        elif player_score == opponent_score:
            ties += 1

    equity = (wins + 0.5 * ties) / simulations
    return equity, f"Monte Carlo ({simulations} simulations)"

# ==============================================================================
# 🔴 ASSUMED EXISTING FUNCTIONS AND CONSTANTS (END)
# ==============================================================================


# ==============================================================================
# 🧠 AI DECISION LOGIC (CORE)
# ==============================================================================

def get_ai_action(ai_equity, current_pot, to_call, ai_stack):
    """
    Determines AI's action based on hand equity against a random range, 
    pot size, and amount to call.
    
    Args:
        ai_equity (float): AI hand equity relative to a random range (0.0 - 1.0).
        current_pot (float): Total current pot (including this round's contributions).
        to_call (float): Amount AI needs to call.
        ai_stack (float): AI's remaining chips.
        
    Returns:
        tuple: (action_type: str, amount: float)
    """
    
    # AI Threshold Settings (Can be adjusted and optimized):
    FOLD_THRESHOLD = 0.30  # Below this equity, tendency to fold (if Pot Odds are bad)
    CALL_THRESHOLD = 0.45  # Requires at least this equity to call, avoids being exploited
    RAISE_THRESHOLD = 0.75 # Far above this equity, tendency to value raise
    BLUFF_PROBABILITY = 0.20 # Bluff frequency
    
    # Calculate minimum bet/raise amount (usually BB or 2x To_Call)
    min_raise = max(st.session_state.bb, 2 * to_call)
    
    # 1. Calculate required equity for a call (Pot Odds)
    if to_call > 0:
        required_equity = to_call / (current_pot + to_call)
    else:
        required_equity = 0
        
    # 2. Decision Logic
    
    if to_call == 0: # AI acts first (Check/Bet)
        
        if ai_equity >= RAISE_THRESHOLD:
            # Strong hand: Value bet (75% of pot)
            bet_amount = 0.75 * current_pot
            return "Bet", min(bet_amount, ai_stack)
        
        elif ai_equity <= FOLD_THRESHOLD and random.random() < BLUFF_PROBABILITY:
            # Weak hand: Bluff (20% frequency, 50% of pot)
            bet_amount = 0.50 * current_pot
            return "Bet", min(bet_amount, ai_stack)
        
        else:
            # Medium hand/Draw: Check to control the pot
            return "Check", 0
            
    else: # Opponent (Player) has bet (Fold/Call/Raise)
        
        # Very strong hand: Raise
        if ai_equity >= RAISE_THRESHOLD:
            raise_amount = min(3 * to_call, ai_stack) # 3 times player's bet
            return "Raise", max(raise_amount, min_raise)
        
        # Hand strong enough to call: Equity is higher than required Pot Odds
        elif ai_equity >= required_equity and ai_equity >= CALL_THRESHOLD:
            return "Call", to_call
            
        # Hand is not strong enough, check for bluff
        elif ai_equity >= required_equity and ai_equity < CALL_THRESHOLD and random.random() < 0.1:
            # Low-frequency bluff raise with slight draws or very weak hands (for range protection)
            raise_amount = min(3 * to_call, ai_stack) 
            return "Raise", max(raise_amount, min_raise)

        else:
            # Fold
            return "Fold", 0

# ==============================================================================
# 🎮 GAME FLOW FUNCTIONS
# ==============================================================================

def init_game_state(initial_stack=1000, bb=20):
    """Initialize new game state"""
    st.session_state.game_active = False # Ensure initial state is waiting to start
    st.session_state.game_over = False # Control showdown display state
    st.session_state.hand_outcome = None # Store non-showdown end message
    st.session_state.player_stack = initial_stack
    st.session_state.ai_stack = initial_stack
    st.session_state.bb = bb
    # Resetting game variables
    st.session_state.current_pot = 0
    st.session_state.board = []
    st.session_state.player_hand = []
    st.session_state.ai_hand = []
    st.session_state.round_street = ""
    st.session_state.to_call = 0 
    st.session_state.known_cards = []

def start_new_hand():
    """Start a new hand: shuffle, deal, and initial blinds"""
    if st.session_state.player_stack <= 0 or st.session_state.ai_stack <= 0:
        st.error("Insufficient chips, please reset the game.")
        st.session_state.game_active = False
        return

    deck = Deck()
    
    # Draw 4 hole cards
    all_known = deck.draw(4) 
    player_hand_int = all_known[:2]
    ai_hand_int = all_known[2:]
    
    st.session_state.game_active = True
    st.session_state.player_hand = player_hand_int
    st.session_state.ai_hand = ai_hand_int
    st.session_state.board = []
    st.session_state.round_street = "Preflop"
    st.session_state.to_call = st.session_state.bb # Player needs to call BB
    st.session_state.current_pot = 0 
    
    # Blind handling: Assume Player is SB (1/2 BB), AI is BB (BB)
    sb = st.session_state.bb / 2
    bb = st.session_state.bb
    
    # Commit blinds
    st.session_state.player_stack -= sb
    st.session_state.ai_stack -= bb
    st.session_state.current_pot = sb + bb
    
    st.session_state.known_cards = player_hand_int + ai_hand_int
    
    st.success(f"Hand starts! Pot {st.session_state.current_pot} (Player contributes {sb}, AI contributes {bb}).")


def advance_street():
    """Advance to the next street (Flop, Turn, River) and reset to_call"""
    
    new_cards = []
    
    # Ensure known cards include all dealt cards
    known_cards_int = st.session_state.player_hand + st.session_state.ai_hand + st.session_state.board
    
    # CORE FIX: Create a temporary full_deck_list and remove known cards
    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR] 
    
    # Get available card pool
    available_cards = [c for c in full_deck_int if c not in known_cards_int]
    
    num_draw = 0
    if st.session_state.round_street == "Preflop":
        num_draw = 3  # Flop
        st.session_state.round_street = "Flop"
    
    elif st.session_state.round_street == "Flop":
        num_draw = 1  # Turn
        st.session_state.round_street = "Turn"
        
    elif st.session_state.round_street == "Turn":
        num_draw = 1  # River
        st.session_state.round_street = "River"
    
    else: 
        return 

    if num_draw > 0 and len(available_cards) >= num_draw:
        # Randomly draw N cards from the available pool
        new_cards = random.sample(available_cards, num_draw)
        st.session_state.board.extend(new_cards)
    else:
        # Safety measure if deck is insufficient
        st.error(f"Cannot draw {num_draw} cards, deck insufficient.")

    st.session_state.to_call = 0 
    st.info(f"🎉 Entering **{st.session_state.round_street}** stage!")
    
def end_hand_showdown(player_hand, ai_hand, board, pot):
    """Showdown and determine the winner"""
    evaluator = Evaluator()
    # 1. Get scores
    player_score = evaluator.evaluate(player_hand, board)
    ai_score = evaluator.evaluate(ai_hand, board)

    # 2. Get hand ranking string
    try:
        player_rank = evaluator.get_rank_string(player_score)
        ai_rank = evaluator.get_rank_string(ai_score)
    except AttributeError:
        # Fallback if get_rank_string is not available
        player_rank = f"Score: {player_score}"
        ai_rank = f"Score: {ai_score}"
        st.warning("⚠️ Could not retrieve hand rank name. Comparing using scores.")

    st.subheader("💰 Showdown Results 💰")
    st.markdown(f"**AI Hand (Opponent):** {' '.join([format_card_to_emoji(Card.int_to_str(c)) for c in ai_hand])}")
    st.markdown(f"Your Hand: **{player_rank}** vs. AI Hand: **{ai_rank}**")
    
    if player_score < ai_score:
        st.success(f"🎊 **You win!** Won {pot} chips.")
        st.session_state.player_stack += pot
    elif player_score > ai_score:
        st.error(f"😔 **AI wins.** Lost {pot} chips.")
        st.session_state.ai_stack += pot
    else:
        st.warning(f"🤝 **Split Pot!** Pot of {pot} chips is divided.")
        half_pot = pot / 2
        st.session_state.player_stack += half_pot
        st.session_state.ai_stack += half_pot

    st.session_state.game_over = True
    st.session_state.hand_outcome = None # Showdown results will be rendered via the game_over state in main()

# ==============================================================================
# 💻 STREAMLIT INTERFACE AND MAIN CONTROL FLOW
# ==============================================================================

def main():
    st.set_page_config(page_title="♠️ Texas Hold'em AI Simulator", layout="centered")
    st.title("♠️ Texas Hold'em AI Simulator")
    st.markdown("---")


    # 1. Initialize Game State
    if 'game_active' not in st.session_state:
        init_game_state()

    # Stacks and Pot Display
    col_stacks, col_pot = st.columns(2)
    col_stacks.metric("Player Stack", st.session_state.player_stack)
    col_stacks.metric("AI Stack", st.session_state.ai_stack)
    col_pot.metric("Current Pot", st.session_state.current_pot)
    st.markdown("---")


        
    # 2. 🔴 Game Over State Handling
    if st.session_state.game_over:
        
        # Render Hole Cards and Board (needed for both Fold and Showdown)
        player_hand_emoji = [format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.player_hand]
        st.markdown(f"**Your Hand (You):** {' '.join(player_hand_emoji)}")
        board_emoji = [format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.board]
        st.markdown(f"**Community Cards (Board):** {(' '.join(board_emoji) if board_emoji else '---')}")
        st.markdown("---")

        if st.session_state.hand_outcome:
            # 🔴 Non-Showdown Finish (Fold)
            st.error("Hand ended early!")
            st.warning(st.session_state.hand_outcome)
        
        else:
            # 🟢 Showdown Finish
            st.success("Hand Over! See showdown results.")
            
            # Re-render showdown results (logic inline for clarity)
            evaluator = Evaluator()
            player_score = evaluator.evaluate(st.session_state.player_hand, st.session_state.board)
            ai_score = evaluator.evaluate(st.session_state.ai_hand, st.session_state.board)
            
            try:
                player_rank = evaluator.get_rank_string(player_score)
                ai_rank = evaluator.get_rank_string(ai_score)
            except AttributeError:
                player_rank = f"Score: {player_score}"
                ai_rank = f"Score: {ai_score}"

            st.subheader("💰 Final Showdown Results 💰")
            st.markdown(f"**AI Hand (Opponent):** {' '.join([format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.ai_hand])}")
            st.markdown(f"Your Hand: **{player_rank}** vs. AI Hand: **{ai_rank}**")
            
            # Final win/loss message (rendered again to be visible in game_over state)
            pot = st.session_state.current_pot
            if player_score < ai_score:
                st.success(f"🎊 **You win!** Won {pot} chips.")
            elif player_score > ai_score:
                st.error(f"😔 **AI wins.** Lost {pot} chips.")
            else:
                st.warning(f"🤝 **Split Pot!** Pot of {pot} chips is divided.")
                
        # Always display new hand button
        if st.button("Start New Hand"):
            start_new_hand()
            st.session_state.game_over = False
            st.session_state.hand_outcome = None # Clear state
            st.rerun()
        return # Block rendering of subsequent betting area
        
    # 2. Game Start Control
    if not st.session_state.game_active:
        if st.button("Start New Hand (SB/BB)"):
            start_new_hand()
            st.rerun()
        if st.session_state.player_stack <= 0 or st.session_state.ai_stack <= 0:
            st.warning("One player is out of chips, please reset the game.")
            if st.button("Reset Entire Game (1000 chips)"):
                 init_game_state()
                 st.rerun()
        return

    # 3. In-Game Display
    
    # Card Info
    st.subheader(f"Current Street: {st.session_state.round_street}")
    player_hand_emoji = [format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.player_hand]
    board_emoji = [format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.board]
    
    st.markdown(f"**Your Hand (You):** {' '.join(player_hand_emoji)}")
    st.markdown(f"**Community Cards (Board):** {(' '.join(board_emoji) if board_emoji else '---')}")

    # 4. Equity and AI Decision
    
    # Preflop simplified handling
    if st.session_state.round_street == "Preflop":
        player_equity = 0.5
        ai_equity = 0.5
        st.info("Preflop Base Equity (50%)")
    else:
        # Real-time equity calculation
        player_equity, _ = calculate_equity(st.session_state.player_hand, st.session_state.board)
        ai_equity, _ = calculate_equity(st.session_state.ai_hand, st.session_state.board)
        
        st.info(f"📈 **Your Current Equity (Vs. Random Hand): {player_equity * 100:.2f}%**")
        # AI's equity is secret
        # st.info(f"🤖 **AI Base Equity (Vs. Random Hand): {ai_equity * 100:.2f}%**")
    st.markdown("---")
    
    # 5. Player Action Area and AI Flow Control
    
    current_pot = st.session_state.current_pot
    to_call = st.session_state.to_call
    
    st.subheader("Your Action")
    if to_call > 0:
        st.markdown(f"Current Call Required: **{to_call}** chips.")
        
    action_col1, action_col2, action_col3 = st.columns(3)
    
    # --- Flow Control Functions ---
    def handle_ai_turn():
        """Handle AI response to player action"""
        
        # Re-calculate AI equity (if not Preflop)
        if st.session_state.round_street != "Preflop":
            ai_equity, _ = calculate_equity(st.session_state.ai_hand, st.session_state.board)
        else:
            ai_equity = 0.5 
            
        with st.spinner("🤖 AI is thinking..."):
            time.sleep(1) # Simulate thinking time
            ai_action, ai_amount = get_ai_action(ai_equity, st.session_state.current_pot, st.session_state.to_call, st.session_state.ai_stack)
            
        return ai_action, ai_amount

    def advance_game_state():
        """Check for showdown or advance to next street"""
        if st.session_state.round_street == "River" and st.session_state.to_call == 0:
            end_hand_showdown(st.session_state.player_hand, st.session_state.ai_hand, st.session_state.board, st.session_state.current_pot)
        elif st.session_state.to_call == 0:
            advance_street()
        st.rerun()
        
    # --- Player Action Button Logic ---
    
    # 1. Fold / Check
    if to_call > 0:
        # Fold
        if action_col1.button(f"Fold ❌"):
            current_pot = st.session_state.current_pot
            st.session_state.ai_stack += current_pot
            
            # Set game_over and hand_outcome
            st.session_state.game_over = True
            st.session_state.hand_outcome = f"You folded. AI won {current_pot:.0f} chips."
            
            st.rerun()
    else:
        # Check
        if action_col1.button(f"Check ✅"):
            st.success("You checked.")
            ai_action, ai_amount = handle_ai_turn()
            
            if ai_action == "Check":
                st.info("AI also checked.")
                advance_game_state()
            else: # AI Bet
                bet_amount = ai_amount
                st.warning(f"AI bets {bet_amount:.0f} chips.")
                st.session_state.ai_stack -= bet_amount
                st.session_state.current_pot += bet_amount
                st.session_state.to_call = bet_amount
                st.rerun()

    # 2. Call
    if to_call > 0:
        if action_col2.button(f"Call {to_call:.0f} chips"):
            
            st.session_state.player_stack -= to_call
            st.session_state.current_pot += to_call
            st.success(f"You called {to_call:.0f} chips.")
            
            st.session_state.to_call = 0 
            advance_game_state()

    # 3. Bet/Raise
    # Minimum raise amount
    min_raise_amount = max(st.session_state.bb, 2 * to_call) 
    # Player's remaining stack (Max Bet/Raise)
    max_bet_raise = st.session_state.player_stack 
    
    # Determine the minimum display value for number_input, respecting all-in limit
    input_min_value = min(min_raise_amount, max_bet_raise) 
    
    # If player cannot afford the standard min raise, min_value becomes all-in amount
    if max_bet_raise < min_raise_amount:
        input_min_value = max_bet_raise

    # Ensure value is never less than min_value
    initial_value = min(input_min_value, max_bet_raise)


    bet_raise_amount_input = action_col3.number_input(
        f"{'Raise' if to_call > 0 else 'Bet'} Amount (Min: {input_min_value:.0f})",
        min_value=float(input_min_value),
        max_value=float(max_bet_raise),
        step=float(st.session_state.bb),
        value=float(initial_value),
        key="bet_raise_input"
    )
    
    if action_col3.button(f"{'Raise' if to_call > 0 else 'Bet'}", key="bet_raise_btn"):
        
        new_bet_size = bet_raise_amount_input
        
        # Total chips contributed by player this action
        total_chips_in = new_bet_size 
        
        st.session_state.player_stack -= total_chips_in
        st.session_state.current_pot += total_chips_in
        
        st.success(f"You {'raised' if to_call > 0 else 'bet'} {new_bet_size:.0f} chips.")
        
        # Amount AI needs to call (Player's total bet)
        st.session_state.to_call = new_bet_size 
        
        # --- AI Response to Player's Bet/Raise ---
        ai_action, ai_amount = handle_ai_turn()
        
        if ai_action == "Fold":
            current_pot = st.session_state.current_pot
            st.session_state.player_stack += current_pot
            
            # Set game_over and hand_outcome
            st.session_state.game_over = True
            st.session_state.hand_outcome = f"AI folded! You won {current_pot:.0f} chips."
            
        elif ai_action == "Call":
            call_amount = st.session_state.to_call
            st.warning(f"AI called {call_amount:.0f} chips.")
            st.session_state.ai_stack -= call_amount
            st.session_state.current_pot += call_amount
            
            st.session_state.to_call = 0 
            advance_game_state()
            
        elif ai_action == "Raise":
            raise_amount = ai_amount
            # Total chips AI commits
            ai_total_in = raise_amount 
            
            st.error(f"AI raised to {ai_total_in:.0f} chips!")
            st.session_state.ai_stack -= ai_total_in
            st.session_state.current_pot += ai_total_in
            
            # Amount player needs to call (AI's total commitment)
            st.session_state.to_call = ai_total_in
            
        st.rerun()

if __name__ == "__main__":
    main()