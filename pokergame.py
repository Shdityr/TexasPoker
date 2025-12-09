import streamlit as st
from deuces.card import Card
from deuces.deck import Deck
from deuces.evaluator import Evaluator
import random
from itertools import combinations
import time  # Used only to simulate AI thinking time


RANKS = '23456789TJQKA'
SUITS = 'shdc'

def create_all_cards():
    """Generate all valid card strings (e.g., 'As', 'Td', etc.)."""
    all_cards_str = []
    for rank in RANKS:
        for suit in SUITS:
            all_cards_str.append(rank + suit)
    return all_cards_str

ALL_CARDS_STR = create_all_cards()

def format_card_to_emoji(card_str):
    """Convert a card like 'As' into a human-readable emoji representation."""
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
    """Convert an emoji card (e.g., 'A♠️') back into a Deuces integer."""
    try:
        index = EMOJI_CARDS.index(emoji_card)
        deuces_str = ALL_CARDS_STR[index]
        return Card.new(deuces_str)
    except ValueError:
        return None

# Equity calculation function (kept as-is; comments clarified)
@st.cache_data
def calculate_equity(player_hand_int, board_int, simulations=25000):
    """
    Estimate hand equity using Monte Carlo simulation.
    Returns (equity, description).
    """
    evaluator = Evaluator()
    wins = 0
    ties = 0
    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR]

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


def get_ai_action(ai_equity, current_pot, to_call, ai_stack):
    """
    Determine the AI action (fold / call / raise / bet / check) based on
    equity versus a random range, pot size, and the required call amount.

    Args:
        ai_equity (float): AI hand equity (0.0 to 1.0).
        current_pot (float): Current total pot.
        to_call (float): Chips required to call.
        ai_stack (float): AI’s remaining chips.

    Returns:
        tuple: (action_type: str, amount: float)
    """

    # Tunable thresholds for the AI decision model.
    FOLD_THRESHOLD = 0.30
    CALL_THRESHOLD = 0.45
    RAISE_THRESHOLD = 0.75
    BLUFF_PROBABILITY = 0.20

    # Minimum legal raise (depends on big blind or 2× call size)
    min_raise = max(st.session_state.bb, 2 * to_call)

    # Compute the pot odds threshold for calling
    if to_call > 0:
        required_equity = to_call / (current_pot + to_call)
    else:
        required_equity = 0

    # --- Decision Logic ---
    if to_call == 0:  # AI is first to act
        if ai_equity >= RAISE_THRESHOLD:
            bet_amount = 0.75 * current_pot
            return "Bet", min(bet_amount, ai_stack)

        elif ai_equity <= FOLD_THRESHOLD and random.random() < BLUFF_PROBABILITY:
            bet_amount = 0.50 * current_pot
            return "Bet", min(bet_amount, ai_stack)

        else:
            return "Check", 0

    else:  # Player has bet; AI responds
        if ai_equity >= RAISE_THRESHOLD:
            raise_amount = min(3 * to_call, ai_stack)
            return "Raise", max(raise_amount, min_raise)

        elif ai_equity >= required_equity and ai_equity >= CALL_THRESHOLD:
            return "Call", to_call

        elif ai_equity >= required_equity and ai_equity < CALL_THRESHOLD and random.random() < 0.1:
            raise_amount = min(3 * to_call, ai_stack)
            return "Raise", max(raise_amount, min_raise)

        else:
            return "Fold", 0


# ==============================================================================
# 🎮 GAME FLOW FUNCTIONS
# ==============================================================================

def init_game_state(initial_stack=1000, bb=20):
    """Initialize session state for a new match."""
    st.session_state.game_active = False
    st.session_state.game_over = False
    st.session_state.hand_outcome = None
    st.session_state.player_stack = initial_stack
    st.session_state.ai_stack = initial_stack
    st.session_state.bb = bb

    st.session_state.current_pot = 0
    st.session_state.board = []
    st.session_state.player_hand = []
    st.session_state.ai_hand = []
    st.session_state.round_street = ""
    st.session_state.to_call = 0
    st.session_state.known_cards = []

def start_new_hand():
    """Start a new hand by shuffling, dealing, and posting blinds."""
    if st.session_state.player_stack <= 0 or st.session_state.ai_stack <= 0:
        st.error("A player has no chips remaining. Please reset the game.")
        st.session_state.game_active = False
        return

    deck = Deck()

    # Deal 4 hole cards: 2 to player, 2 to AI
    all_known = deck.draw(4)
    player_hand_int = all_known[:2]
    ai_hand_int = all_known[2:]

    st.session_state.game_active = True
    st.session_state.player_hand = player_hand_int
    st.session_state.ai_hand = ai_hand_int
    st.session_state.board = []
    st.session_state.round_street = "Preflop"
    st.session_state.to_call = st.session_state.bb
    st.session_state.current_pot = 0

    # Post blinds: Player = SB, AI = BB
    sb = st.session_state.bb / 2
    bb = st.session_state.bb

    st.session_state.player_stack -= sb
    st.session_state.ai_stack -= bb
    st.session_state.current_pot = sb + bb

    st.session_state.known_cards = player_hand_int + ai_hand_int

    st.success(f"The hand begins! Pot: {st.session_state.current_pot} "
               f"(Player posted {sb}, AI posted {bb}).")

def advance_street():
    """Move to the next street (Flop → Turn → River) and deal the community cards."""
    new_cards = []
    known_cards_int = st.session_state.player_hand + st.session_state.ai_hand + st.session_state.board

    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR]
    available_cards = [c for c in full_deck_int if c not in known_cards_int]

    num_draw = 0

    if st.session_state.round_street == "Preflop":
        num_draw = 3
        st.session_state.round_street = "Flop"

    elif st.session_state.round_street == "Flop":
        num_draw = 1
        st.session_state.round_street = "Turn"

    elif st.session_state.round_street == "Turn":
        num_draw = 1
        st.session_state.round_street = "River"

    else:
        return

    if num_draw > 0 and len(available_cards) >= num_draw:
        new_cards = random.sample(available_cards, num_draw)
        st.session_state.board.extend(new_cards)
    else:
        st.error(f"Unable to deal {num_draw} community cards.")

    st.session_state.to_call = 0
    st.info(f"Now entering the **{st.session_state.round_street}** stage.")

def end_hand_showdown(player_hand, ai_hand, board, pot):
    """Display showdown results and distribute the pot."""
    evaluator = Evaluator()

    player_score = evaluator.evaluate(player_hand, board)
    ai_score = evaluator.evaluate(ai_hand, board)

    try:
        player_rank = evaluator.get_rank_string(player_score)
        ai_rank = evaluator.get_rank_string(ai_score)
    except AttributeError:
        player_rank = f"Score: {player_score}"
        ai_rank = f"Score: {ai_score}"
        st.warning("Unable to retrieve descriptive hand ranks. Scores shown instead.")

    st.subheader("💰 Showdown Results 💰")
    st.markdown(
        f"**AI Hand:** {' '.join([format_card_to_emoji(Card.int_to_str(c)) for c in ai_hand])}"
    )
    st.markdown(f"Your Hand: **{player_rank}** vs. AI Hand: **{ai_rank}**")

    if player_score < ai_score:
        st.success(f"🎊 You win the pot of {pot} chips!")
        st.session_state.player_stack += pot
    elif player_score > ai_score:
        st.error(f"😔 AI wins and collects {pot} chips.")
        st.session_state.ai_stack += pot
    else:
        st.warning(f"🤝 It's a split pot! Each receives {pot / 2} chips.")
        half = pot / 2
        st.session_state.player_stack += half
        st.session_state.ai_stack += half

    st.session_state.game_over = True
    st.session_state.hand_outcome = None


# ==============================================================================
# 💻 STREAMLIT INTERFACE AND MAIN APPLICATION LOGIC
# ==============================================================================

def main():
    st.set_page_config(page_title="♠️ Texas Hold'em AI Simulator", layout="centered")
    st.title("♠️ Texas Hold'em AI Simulator")
    st.markdown("---")

    # 1. Initialize state if first load
    if 'game_active' not in st.session_state:
        init_game_state()

    # Display stacks and pot
    col_stacks, col_pot = st.columns(2)
    col_stacks.metric("Player Stack", st.session_state.player_stack)
    col_stacks.metric("AI Stack", st.session_state.ai_stack)
    col_pot.metric("Current Pot", st.session_state.current_pot)
    st.markdown("---")

    # 2. Handle game-over state (fold or showdown)
    if st.session_state.game_over:

        player_hand_emoji = [format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.player_hand]
        board_emoji = [format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.board]

        st.markdown(f"**Your Hand:** {' '.join(player_hand_emoji)}")
        st.markdown(f"**Board:** {(' '.join(board_emoji) if board_emoji else '---')}")
        st.markdown("---")

        if st.session_state.hand_outcome:
            st.error("The hand ended before showdown.")
            st.warning(st.session_state.hand_outcome)
        else:
            st.success("The hand is over. See the final results below.")

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
            st.markdown(
                f"**AI Hand:** {' '.join([format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.ai_hand])}"
            )
            st.markdown(f"Your Hand: **{player_rank}** vs. AI Hand: **{ai_rank}**")

            pot = st.session_state.current_pot
            if player_score < ai_score:
                st.success(f"🎊 You win {pot} chips!")
            elif player_score > ai_score:
                st.error(f"😔 AI wins {pot} chips.")
            else:
                st.warning("🤝 Split pot.")

        if st.button("Start New Hand"):
            start_new_hand()
            st.session_state.game_over = False
            st.session_state.hand_outcome = None
            st.rerun()

        return

    # 3. Start-hand controls
    if not st.session_state.game_active:
        if st.button("Start New Hand (SB/BB)"):
            start_new_hand()
            st.rerun()
        if st.session_state.player_stack <= 0 or st.session_state.ai_stack <= 0:
            st.warning("A player is out of chips. Reset to continue.")
            if st.button("Reset Game (1000 chips)"):
                init_game_state()
                st.rerun()
        return

    # 4. In-hand display
    st.subheader(f"Current Street: {st.session_state.round_street}")

    player_hand_emoji = [format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.player_hand]
    board_emoji = [format_card_to_emoji(Card.int_to_str(c)) for c in st.session_state.board]

    st.markdown(f"**Your Hand:** {' '.join(player_hand_emoji)}")
    st.markdown(f"**Board:** {(' '.join(board_emoji) if board_emoji else '---')}")

    # 5. Equity display
    if st.session_state.round_street == "Preflop":
        player_equity = 0.5
        ai_equity = 0.5
        st.info("Preflop Equity (approx.): 50% each.")
    else:
        player_equity, _ = calculate_equity(st.session_state.player_hand, st.session_state.board)
        ai_equity, _ = calculate_equity(st.session_state.ai_hand, st.session_state.board)

        st.info(f"📈 Your Estimated Equity vs a Random Hand: **{player_equity * 100:.2f}%**")

    st.markdown("---")

    # 6. Player Action Area
    current_pot = st.session_state.current_pot
    to_call = st.session_state.to_call

    st.subheader("Your Action")
    if to_call > 0:
        st.markdown(f"You must call **{to_call}** chips.")

    action_col1, action_col2, action_col3 = st.columns(3)

    # --- Helper functions ---
    def handle_ai_turn():
        """Recalculate AI equity and return its response."""
        if st.session_state.round_street != "Preflop":
            ai_equity, _ = calculate_equity(st.session_state.ai_hand, st.session_state.board)
        else:
            ai_equity = 0.5

        with st.spinner("🤖 AI is thinking..."):
            time.sleep(0.5)
            ai_action, ai_amount = get_ai_action(ai_equity, st.session_state.current_pot, st.session_state.to_call, st.session_state.ai_stack)

        return ai_action, ai_amount

    def advance_game_state():
        """
        After both players act, either:
        - deal the next community card(s),
        - or go to showdown on the river.
        """
        if st.session_state.round_street == "River" and st.session_state.to_call == 0:
            end_hand_showdown(st.session_state.player_hand, st.session_state.ai_hand, st.session_state.board, st.session_state.current_pot)
        elif st.session_state.to_call == 0:
            advance_street()
        st.rerun()

    # --- Player Buttons ---

    # 1. Fold or Check
    if to_call > 0:
        if action_col1.button("Fold ❌"):
            current_pot = st.session_state.current_pot
            st.session_state.ai_stack += current_pot

            st.session_state.game_over = True
            st.session_state.hand_outcome = f"You folded. AI collects {current_pot:.0f} chips."

            st.rerun()
    else:
        if action_col1.button("Check ✅"):
            st.success("You check.")
            ai_action, ai_amount = handle_ai_turn()

            if ai_action == "Check":
                st.info("AI checks behind.")
                time.sleep(2)
                advance_game_state()
            else:
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
            st.success(f"You call {to_call:.0f} chips.")
            time.sleep(1)

            st.session_state.to_call = 0
            advance_game_state()

    # 3. Bet / Raise
    min_raise_amount = max(st.session_state.bb, 2 * to_call)
    max_bet_raise = st.session_state.player_stack

    input_min_value = min(min_raise_amount, max_bet_raise)

    if max_bet_raise < min_raise_amount:
        input_min_value = max_bet_raise

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

        st.session_state.player_stack -= new_bet_size
        st.session_state.current_pot += new_bet_size

        st.success(f"You {'raised' if to_call > 0 else 'bet'} {new_bet_size:.0f} chips.")

        st.session_state.to_call = new_bet_size

        ai_action, ai_amount = handle_ai_turn()

        if ai_action == "Fold":
            current_pot = st.session_state.current_pot
            st.session_state.player_stack += current_pot

            st.session_state.game_over = True
            st.session_state.hand_outcome = f"AI folds — you win {current_pot:.0f} chips."
            time.sleep(2)

        elif ai_action == "Call":
            call_amount = st.session_state.to_call
            st.warning(f"AI calls {call_amount:.0f} chips.")
            time.sleep(2)
            st.session_state.ai_stack -= call_amount
            st.session_state.current_pot += call_amount

            st.session_state.to_call = 0
            advance_game_state()

        elif ai_action == "Raise":
            raise_amount = ai_amount
            st.error(f"AI raises to {raise_amount:.0f} chips!")
            time.sleep(2)
            st.session_state.ai_stack -= raise_amount
            st.session_state.current_pot += raise_amount

            st.session_state.to_call = raise_amount

        st.rerun()

if __name__ == "__main__":
    main()
