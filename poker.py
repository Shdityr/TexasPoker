import streamlit as st
from deuces.card import Card
from deuces.deck import Deck
from deuces.evaluator import Evaluator
import random
from itertools import combinations

## --- 1. Card Constants and Conversion Functions ---

RANKS = '23456789TJQKA'
SUITS = 'shdc' # s=Spades, h=Hearts, d=Diamonds, c=Clubs

def create_all_cards():
    """Generates a list of 52 card strings in deuces format ('Ah', 'Ks', ...)"""
    all_cards_str = []
    for rank in RANKS:
        for suit in SUITS:
            all_cards_str.append(rank + suit)
    return all_cards_str

ALL_CARDS_STR = create_all_cards()

def format_card_to_emoji(card_str):
    """Converts a card in 'As' format to the graphical 'A♠️' format"""
    if not card_str or len(card_str) != 2:
        return card_str
        
    rank = card_str[0].upper()
    suit_char = card_str[1].lower()
    
    suit_map = {'s': '♠️', 'h': '♥️', 'd': '♦️', 'c': '♣️'}
    rank_map = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}
    
    display_rank = rank_map.get(rank, rank)
    display_suit = suit_map.get(suit_char, '')
    
    return f"{display_rank}{display_suit}"

# Generate the graphical list for Streamlit select boxes
EMOJI_CARDS = [format_card_to_emoji(c) for c in ALL_CARDS_STR]

def convert_emoji_to_deuces_int(emoji_card):
    """Converts a card in 'A♥️' format to the integer representation used by the deuces library"""
    try:
        # Find the index of the emoji card in the graphical list
        index = EMOJI_CARDS.index(emoji_card)
        # Use the same index to get the deuces string ('Ah')
        deuces_str = ALL_CARDS_STR[index]
        # Convert to deuces integer
        return Card.new(deuces_str)
    except ValueError:
        return None

## --- 2. Equity Calculation Functions ---

# --- Exact Calculation Function (Unchanged) ---
def enumerate_equity(player_hand_int, board_int):
    """
    Calculates exact equity by iterating over all remaining valid combinations 
    when the number of community cards is 4 or 5.
    """
    evaluator = Evaluator()
    wins = 0
    ties = 0
    total_sims = 0

    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR] 
    known_cards = player_hand_int + board_int
    unknown_pool = [c for c in full_deck_int if c not in known_cards]

    num_board = len(board_int)
    
    needed_for_opp = 2
    needed_for_board = 5 - num_board
    
    needed_total = needed_for_opp + needed_for_board
    
    for drawn_cards in combinations(unknown_pool, needed_total):
        
        opponent_hand = list(drawn_cards[:needed_for_opp])
        remaining_board = list(drawn_cards[needed_for_opp:])
        final_board = board_int + remaining_board
        
        player_score = evaluator.evaluate(player_hand_int, final_board)
        opponent_score = evaluator.evaluate(opponent_hand, final_board)

        if player_score < opponent_score:
            wins += 1
        elif player_score == opponent_score:
            ties += 1
        
        total_sims += 1
        
    if total_sims == 0:
        return 0.0, 0
    
    equity = (wins + 0.5 * ties) / total_sims
    return equity, total_sims


# --- Main Calculation Function (Unchanged) ---
@st.cache_data
def calculate_equity(player_hand_int, board_int, simulations=10000):
    
    if len(player_hand_int) != 2:
        return 0.0, "N/A" 

    num_board = len(board_int)
    
    if num_board >= 4:
        equity, total_sims = enumerate_equity(player_hand_int, board_int)
        return equity, f"Exact Calculation ({total_sims} iterations)"

    evaluator = Evaluator()
    wins = 0
    ties = 0
    
    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR] 

    for _ in range(simulations):
        known_cards = player_hand_int + board_int
        unknown_pool = [c for c in full_deck_int if c not in known_cards]
        
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

## --- 3. Streamlit Application Interface and Random Functions ---

st.set_page_config(page_title="♠️ Heads-Up Poker Equity Calculator", layout="centered")
st.title("♠️ Heads-Up Poker Equity Calculator")
st.markdown("---")

# Initialize Session State
if 'h1_emoji' not in st.session_state:
    st.session_state.h1_emoji = EMOJI_CARDS[0]
if 'h2_emoji' not in st.session_state:
    st.session_state.h2_emoji = [c for c in EMOJI_CARDS if c != st.session_state.h1_emoji][1]
if 'flop_emoji' not in st.session_state:
    st.session_state.flop_emoji = []
if 'turn_emoji' not in st.session_state:
    st.session_state.turn_emoji = ""
if 'river_emoji' not in st.session_state:
    st.session_state.river_emoji = ""

def get_available_cards(exclude_list):
    """Gets the list of available cards"""
    return [c for c in EMOJI_CARDS if c not in exclude_list]

def random_hole_cards():
    """Randomly selects two hole cards"""
    available = get_available_cards([])
    random_hand = random.sample(available, 2)
    st.session_state.h1_emoji = random_hand[0]
    st.session_state.h2_emoji = random_hand[1]

# --- NEW: Independent Community Card Randomization Functions ---
def random_flop_cards():
    """Randomly selects 3 flop cards"""
    current_hand = [st.session_state.h1_emoji, st.session_state.h2_emoji]
    known_cards = current_hand + ([st.session_state.turn_emoji] if st.session_state.turn_emoji else []) + ([st.session_state.river_emoji] if st.session_state.river_emoji else [])
    
    available = get_available_cards(known_cards)
    
    if len(available) >= 3:
        st.session_state.flop_emoji = random.sample(available, 3)
    else:
        st.warning("Not enough cards left in the pool to randomize the flop.")

def random_turn_card():
    """Randomly selects 1 turn card"""
    current_hand = [st.session_state.h1_emoji, st.session_state.h2_emoji]
    known_cards = current_hand + st.session_state.flop_emoji + ([st.session_state.river_emoji] if st.session_state.river_emoji else [])
    
    available = get_available_cards(known_cards)

    if len(available) >= 1:
        st.session_state.turn_emoji = random.sample(available, 1)[0]
    else:
        st.session_state.turn_emoji = ""
        st.warning("No available cards left to randomize the turn.")

def random_river_card():
    """Randomly selects 1 river card"""
    current_hand = [st.session_state.h1_emoji, st.session_state.h2_emoji]
    known_cards = current_hand + st.session_state.flop_emoji + ([st.session_state.turn_emoji] if st.session_state.turn_emoji else [])
    
    available = get_available_cards(known_cards)

    if len(available) >= 1:
        st.session_state.river_emoji = random.sample(available, 1)[0]
    else:
        st.session_state.river_emoji = ""
        st.warning("No available cards left to randomize the river.")
# --- END NEW: Independent Community Card Randomization Functions ---


# ----------------------------------------------------
# 1. Your Hole Cards
# ----------------------------------------------------
st.header("1. Your Hole Cards")

# Set hole cards random button
col_h_manual, col_h_random = st.columns([0.7, 0.3])
with col_h_random:
    st.markdown(" ") # Used for alignment
    if st.button("🔀 Random Hand", key="random_hand_btn"):
        random_hole_cards()
        st.rerun() 

# Manual hole card selection
h_col1, h_col2 = col_h_manual.columns(2)
with h_col1:
    h1_emoji = st.selectbox(
        "First Card", 
        EMOJI_CARDS, 
        key="h1_emoji", 
        index=EMOJI_CARDS.index(st.session_state.h1_emoji)
    )

# Dynamically update the second card options, excluding the first card
h2_options = [c for c in EMOJI_CARDS if c != h1_emoji]
try:
    h2_index = h2_options.index(st.session_state.h2_emoji)
except ValueError:
    h2_index = 0
    st.session_state.h2_emoji = h2_options[0] 
    
with h_col2:
    h2_emoji = st.selectbox(
        "Second Card", 
        h2_options, 
        key="h2_emoji",
        index=h2_index
    )

all_selected_cards = [h1_emoji, h2_emoji]


# ----------------------------------------------------
# 2. Community Cards (Board)
# ----------------------------------------------------
st.header("2. Community Cards (Board)")

# --- Flop ---
col_f_manual, col_f_random = st.columns([0.7, 0.3])
with col_f_random:
    if st.button("🔀 Random Flop (3 Cards)", key="random_flop_btn"):
        random_flop_cards()
        st.rerun()

# Dynamically update flop options
board_options_flop = get_available_cards(all_selected_cards)
with col_f_manual:
    flop_emoji = st.multiselect(
        "Flop (0 or 3 Cards)", 
        board_options_flop, 
        max_selections=3, 
        default=st.session_state.flop_emoji,
        key="flop_emoji"
    )
all_selected_cards.extend(flop_emoji)

# --- Turn ---
col_t_manual, col_t_random = st.columns([0.7, 0.3])
with col_t_random:
    if st.button("🔀 Random Turn (1 Card)", key="random_turn_btn"):
        random_turn_card()
        st.rerun()

# Dynamically update turn options
turn_options = [c for c in EMOJI_CARDS if c not in all_selected_cards]
try:
    # +1 because the empty string "" is at index 0
    turn_index = turn_options.index(st.session_state.turn_emoji) + 1 
except ValueError:
    turn_index = 0
    st.session_state.turn_emoji = "" 
    
with col_t_manual:
    turn_emoji = st.selectbox(
        "Turn (0 or 1 Card)", 
        [""] + turn_options, 
        index=turn_index,
        key="turn_emoji"
    )
if turn_emoji:
    all_selected_cards.append(turn_emoji)

# --- River ---
col_r_manual, col_r_random = st.columns([0.7, 0.3])
with col_r_random:
    if st.button("🔀 Random River (1 Card)", key="random_river_btn"):
        random_river_card()
        st.rerun()

# Dynamically update river options
river_options = [c for c in EMOJI_CARDS if c not in all_selected_cards]
try:
    # +1 because the empty string "" is at index 0
    river_index = river_options.index(st.session_state.river_emoji) + 1 
except ValueError:
    river_index = 0
    st.session_state.river_emoji = "" 
    
with col_r_manual:
    river_emoji = st.selectbox(
        "River (0 or 1 Card)", 
        [""] + river_options, 
        index=river_index,
        key="river_emoji"
    )
if river_emoji:
    all_selected_cards.append(river_emoji)


# ----------------------------------------------------
# 3. Result Calculation
# ----------------------------------------------------
st.markdown("---")
if st.button("🚀 Calculate Current Equity"):
    
    # Check for duplicate cards
    if h1_emoji == h2_emoji:
        st.error("⚠️ Your two hole cards cannot be the same.")
    elif len(set(all_selected_cards)) != len(all_selected_cards):
        st.error("⚠️ There cannot be duplicate cards in the board and hand. Please check your selections.")
    else:
        # Convert all selected Emoji cards to deuces integers
        player_hand_int = [
            convert_emoji_to_deuces_int(h1_emoji), 
            convert_emoji_to_deuces_int(h2_emoji)
        ]
        
        board_int = []
        for emoji in flop_emoji:
            board_int.append(convert_emoji_to_deuces_int(emoji))
        if turn_emoji:
            board_int.append(convert_emoji_to_deuces_int(turn_emoji))
        if river_emoji:
            board_int.append(convert_emoji_to_deuces_int(river_emoji))
        
            
        if len(player_hand_int) == 2:
            with st.spinner('Calculating equity... This might take longer when there are more community cards.'):
                # Call the updated function
                equity, calc_type = calculate_equity(player_hand_int, board_int, simulations=50000)
                
                st.success("✅ **Calculation Complete!**")
                st.markdown(f"## Your current equity is: **{equity * 100:.2f}%**")
                
                st.info(f"Calculation Type: {calc_type}.")
        else:
            st.error("Please select your two hole cards.")