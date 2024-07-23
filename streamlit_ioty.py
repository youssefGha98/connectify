import streamlit as st
from streamlit_option_menu import option_menu
from ICO_distribution import ICOOrchestrator, ICOParticipant
from Liquidity_pool import LiquidityPool
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import matplotlib.pyplot as plt
from staking import StakingCalculator
from vesting_simulation import TokenEconomySimulator
from initial_data_ioty import revenue_data, participant_data
from data_pool import Pool, compute_incentive_emission, distribute_tokens_to_pools

# Constants
LOCKING_YEARS = 1
LOCKING_MONTHS = LOCKING_YEARS * 12

initial_listing_price = 0.03
total_supply = 3_000_000_000

if "revenue_df" not in st.session_state:
    st.session_state.revenue_df = pd.DataFrame(revenue_data)

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(participant_data)


def compute_distribution_scenario(scenario, emission_rate, ratios):
    revenu = st.session_state.revenue_df[scenario]
    token_price = st.session_state.debt_dataframe["token_price"]
    pools = {
        "Treasury": Pool("Treasury", initial_tokens=initial_treasury_tokens),
        "Staking": Pool("Staking", initial_tokens=initial_staking_tokens),
        "Minting": Pool(
            "Minting",
            max_tokens=initial_minting_tokens,
            initial_tokens=initial_minting_tokens,
        ),
    }
    simulation_length = min(len(revenu), len(token_price))
    tokens_to_be_unlocked = [0] * (simulation_length + LOCKING_MONTHS)
    total_tokens_locked = [0] * (simulation_length + LOCKING_MONTHS)
    for month in range(simulation_length):
        tokens_to_be_locked_from_revenu = revenu[month] / token_price[month]
        total_tokens_locked[month] += tokens_to_be_locked_from_revenu
        minting_pool_tokens = pools["Minting"].get_current_tokens()
        minting_emission = compute_incentive_emission(
            total_tokens_locked[month],
            minting_pool_tokens,
            initial_minting_tokens,
            emission_rate,
        )
        pools["Minting"].subtract_tokens(minting_emission)
        staking_emission = st.session_state.staking_data_optimistic[
            "incentive_for_stakers_0"
        ].iloc[month]
        pools["Staking"].subtract_tokens(staking_emission)
        total_tokens_locked[month] += minting_emission
        for i in range(LOCKING_MONTHS):
            if month + LOCKING_MONTHS + i < simulation_length + LOCKING_MONTHS:
                tokens_to_be_unlocked[month + LOCKING_MONTHS + i] += (
                    total_tokens_locked[month] / LOCKING_MONTHS
                )
        distribute_tokens_to_pools(tokens_to_be_unlocked[month], pools, ratios)
        for pool in pools.values():
            pool.update_history()
    return pools


def add_row(
    description,
    percent_of_tot_supply,
    price_per_token,
    tge_percent,
    cliff_months,
    distribution_months,
):
    new_row = pd.DataFrame(
        {
            "description": [description],
            "percent_of_tot_supply": [percent_of_tot_supply],
            "price_per_token": [price_per_token],
            "tge_percent": [tge_percent],
            "cliff_months": [cliff_months],
            "distribution_months": [distribution_months],
        }
    )
    st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)


def add_revenue_scenario(month, pessimistic, moderate, optimistic):
    new_row = pd.DataFrame(
        {
            "month": [month],
            "pessimistic": [pessimistic],
            "moderate": [moderate],
            "optimistic": [optimistic],
        }
    )
    st.session_state.revenue_df = pd.concat(
        [st.session_state.revenue_df, new_row], ignore_index=True
    )


# Navigation menu
with st.sidebar:
    selected = option_menu(
        "Main Menu",
        ["ICO Participants", "Liquidity Pool Setup", "Revenu", "Staking", "Minting"],
        icons=["house", "graph-up"],
        menu_icon="cast",
        default_index=0,
    )

if selected == "ICO Participants":
    st.title("ICO Participants Data Entry")

    with st.form(key="participant_form"):
        description = st.text_input("Description")
        percent_of_tot_supply = st.number_input(
            "Percent of Total Supply", min_value=0.0, max_value=100.0, step=0.01
        )
        price_per_token = st.number_input("Price per Token", min_value=0.0, step=0.0001)
        tge_percent = st.number_input(
            "TGE Percent", min_value=0.0, max_value=100.0, step=0.01
        )
        cliff_months = st.number_input("Cliff Months", min_value=0, step=1)
        distribution_months = st.number_input(
            "Distribution Months", min_value=0, step=1
        )
        submit_button = st.form_submit_button(label="Add Participant")

        if submit_button:
            add_row(
                description,
                percent_of_tot_supply,
                price_per_token,
                tge_percent,
                cliff_months,
                distribution_months,
            )
            st.success(f"Added {description}")

    st.write("Current Participants Data")

    gb = GridOptionsBuilder.from_dataframe(st.session_state.df)
    gb.configure_default_column(editable=True)
    gb.configure_selection("single")
    grid_options = gb.build()

    grid_response = AgGrid(
        st.session_state.df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.VALUE_CHANGED,
        allow_unsafe_jscode=True,
        height=300,
    )

    st.session_state.df = grid_response["data"]

    selected_row = grid_response.get("selected_rows", [])
    if selected_row is not None:
        if st.button(f"Delete {selected_row.values[0][0]}"):
            st.session_state.df = st.session_state.df.drop(
                st.session_state.df.index[
                    st.session_state.df["description"] == selected_row.values[0][0]
                ]
            ).reset_index(drop=True)
            st.experimental_rerun()

    if not st.session_state.df.empty:
        st.session_state.orchestrator = ICOOrchestrator(
            total_supply=total_supply, listing_price=initial_listing_price
        )

        for _, row in st.session_state.df.iterrows():
            participant = ICOParticipant(**row.to_dict())
            st.session_state.orchestrator.add_participant(participant)

        participants_df = (
            st.session_state.orchestrator.create_participants_financial_dataframe()
        )
        st.write("Participants Financial DataFrame")
        st.dataframe(participants_df)

        vesting_schedule_df = (
            st.session_state.orchestrator.create_participants_distribution_dataframe()
        )
        st.write("Vesting Schedule DataFrame")
        st.dataframe(vesting_schedule_df)

        # Generate stacked area chart for vesting schedules
        st.header("Vesting Schedules Stacked Area Chart")
        fig, ax = plt.subplots()
        vesting_schedule_df.cumsum().plot.area(ax=ax, stacked=True, alpha=0.5)
        ax.set_title("Vesting Schedules Over Time")
        ax.set_xlabel("Months")
        ax.set_ylabel("Tokens Vested")
        ax.legend(title="Participants")
        st.pyplot(fig)
        plt.close(fig)

        # Generate pie chart for token allocation
        st.header("Token Allocation Pie Chart")
        allocation_data = st.session_state.df.groupby("description")[
            "percent_of_tot_supply"
        ].sum()
        fig, ax = plt.subplots()
        ax.pie(
            allocation_data,
            labels=allocation_data.index,
            autopct="%1.1f%%",
            startangle=140,
        )
        ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
        ax.set_title("Token Allocation")
        st.pyplot(fig)
        plt.close(fig)
elif selected == "Liquidity Pool Setup":
    st.title("Liquidity Pool Setup")

    if "orchestrator" in st.session_state:
        st.session_state.initial_ioty = st.number_input(
            "Initial ioty in the Liquidity Pool", value=300_000_000
        )
        initial_usdc = st.session_state.initial_ioty * initial_listing_price
        st.session_state.lp = LiquidityPool(initial_usdc, st.session_state.initial_ioty)
        st.text(
            f"You would need {initial_usdc} in order to have a listing price of {initial_listing_price} for this initial liquidity provision"
        )
        initial_token_price = st.number_input("Average trading size", value=10_000.0)
        token_price_decrease_rate = st.number_input(
            "Maximum price impact threshhold", value=-0.0002, format="%.5f"
        )
        mitigation = st.checkbox("Apply mitigation", value=True)

        simulator = TokenEconomySimulator(
            st.session_state.orchestrator,
            st.session_state.lp,
            columns_to_exclude=["Liquidity", "Treasury/community", "Staking"],
        )
        simulator.compute_monthly_released_tokens()
        simulation_result = simulator.run_vesting_simulation(
            initial_token_price, token_price_decrease_rate, with_mitigation=mitigation
        )

        st.session_state.debt_dataframe = pd.DataFrame(simulation_result)
        st.write(st.session_state.debt_dataframe)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(st.session_state.debt_dataframe["usdcs_to_buy"], color="orange")
        ax.set_title("Debt Emission of the Protocol in Dollar")
        ax.set_xlabel("Months")
        ax.set_ylabel("Dollars")
        ax.ticklabel_format(style="plain", axis="y")
        ax.legend()
        ax.grid(False)
        st.pyplot(fig)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(
            st.session_state.debt_dataframe["usdcs_to_buy"].cumsum(), color="orange"
        )
        ax.set_title("Cumulated Debt Emission of the Protocol in Dollar")
        ax.set_xlabel("Months")
        ax.set_ylabel("Dollars")
        ax.ticklabel_format(style="plain", axis="y")
        ax.legend()
        ax.grid(False)
        st.pyplot(fig)

    else:
        st.write("Please set up ICO Participants first.")


elif selected == "Revenu":
    st.title("Revenue Scenarios")

    # Upload file
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            st.session_state.revenue_df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx"):
            st.session_state.revenue_df = pd.read_excel(uploaded_file)

    st.write("Current Revenue Scenarios")
    st.write(st.session_state.revenue_df)
    usdcs_to_buy = pd.DataFrame(
        st.session_state.debt_dataframe["usdcs_to_buy"].to_list() + [0] * 23
    )
    usdcs_to_buy = usdcs_to_buy[usdcs_to_buy[0] != 0]
    scenario_moderate_data = st.session_state.revenue_df["moderate"] - usdcs_to_buy[0]
    scenario_optimistic_data = (
        st.session_state.revenue_df["optimistic"] - usdcs_to_buy[0]
    )
    scenario_pessimistic_data = (
        st.session_state.revenue_df["pessimistic"] - usdcs_to_buy[0]
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(st.session_state.revenue_df["moderate"], label="Moderate", color="blue")
    ax.plot(
        st.session_state.revenue_df["optimistic"], label="Optimistic", color="green"
    )
    ax.plot(
        st.session_state.revenue_df["pessimistic"], label="Pessimistic", color="red"
    )
    ax.set_title("Monthly Revenues by Scenario in Dollars")
    ax.set_xlabel("Time (Months)")
    ax.set_ylabel("Revenues in Dollars")
    ax.ticklabel_format(style="plain", axis="y")
    ax.legend()
    ax.grid(False)
    st.pyplot(fig)

    fig_2, ax_2 = plt.subplots(figsize=(10, 6))
    ax_2.plot(scenario_moderate_data, label="Moderate", color="blue")
    ax_2.plot(scenario_optimistic_data, label="Optimistic", color="green")
    ax_2.plot(scenario_pessimistic_data, label="Pessimistic", color="red")
    ax_2.set_title("Gross profit over time (Revenu VS Debt Emission)")
    ax_2.set_xlabel("Time (Months)")
    ax_2.set_ylabel("Dollars")
    ax_2.ticklabel_format(style="plain", axis="y")
    ax_2.legend()
    ax_2.grid(False)
    st.pyplot(fig_2)

elif selected == "Staking":
    apr_target = st.number_input(
        "Target_apr", min_value=0.0, max_value=1.0, step=0.01, value=0.2
    )

    st.session_state.staking_calculator_moderate = StakingCalculator(
        st.session_state.debt_dataframe["usdcs_to_buy"],
        st.session_state.revenue_df["moderate"],
        st.session_state.debt_dataframe["token_price"],
        apr_target,
    )
    initial_staking_pool = (
        st.session_state.df[st.session_state.df["description"] == "Staking"][
            "percent_of_tot_supply"
        ]
        * total_supply
        / 100
    ).values[0]

    st.session_state.staking_data_moderate = (
        st.session_state.staking_calculator_moderate.compute_incentive_for_stakers(
            1,
            st.session_state.initial_ioty,
            initial_staking_pool,
        )
    )

    st.session_state.staking_calculator_optimistic = StakingCalculator(
        st.session_state.debt_dataframe["usdcs_to_buy"],
        st.session_state.revenue_df["optimistic"],
        st.session_state.debt_dataframe["token_price"],
        apr_target,
    )
    st.session_state.staking_data_optimistic = (
        st.session_state.staking_calculator_optimistic.compute_incentive_for_stakers(
            1,
            st.session_state.initial_ioty,
            initial_staking_pool,
        )
    )

    st.session_state.staking_calculator_pessimistic = StakingCalculator(
        st.session_state.debt_dataframe["usdcs_to_buy"],
        st.session_state.revenue_df["pessimistic"],
        st.session_state.debt_dataframe["token_price"],
        apr_target,
    )
    st.session_state.staking_data_pessimistic = (
        st.session_state.staking_calculator_pessimistic.compute_incentive_for_stakers(
            1,
            st.session_state.initial_ioty,
            initial_staking_pool,
        )
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        st.session_state.staking_data_moderate["percent_staked"],
        label="Moderate",
        color="blue",
    )
    ax.plot(
        st.session_state.staking_data_optimistic["percent_staked"],
        label="Optimistic",
        color="green",
    )
    ax.plot(
        st.session_state.staking_data_pessimistic["percent_staked"],
        label="Pessimistic",
        color="red",
    )
    ax.set_title("Percentage of tokens to be staked over the total supply")
    ax.set_xlabel("Time (Months)")
    ax.set_ylabel("% supply")
    ax.ticklabel_format(style="plain", axis="y")
    ax.legend()
    ax.grid(False)
    st.pyplot(fig)

    fig_2, ax_2 = plt.subplots(figsize=(10, 6))
    ax_2.plot(
        st.session_state.staking_data_moderate["staking_pool"],
        label="Moderate",
        color="blue",
    )
    ax_2.plot(
        st.session_state.staking_data_optimistic["staking_pool"],
        label="Optimistic",
        color="green",
    )
    ax_2.plot(
        st.session_state.staking_data_pessimistic["staking_pool"],
        label="Pessimistic",
        color="red",
    )
    ax_2.set_title("Staking pool status")
    ax_2.set_xlabel("Time (Months)")
    ax_2.set_ylabel("Ioty")
    ax_2.ticklabel_format(style="plain", axis="y")
    ax_2.legend()
    ax_2.grid(False)
    st.pyplot(fig_2)

    fig_3, ax_3 = plt.subplots(figsize=(10, 6))
    ax_3.plot(
        st.session_state.staking_data_moderate["incentive_for_stakers_0"],
        label="Moderate",
        color="blue",
    )
    ax_3.plot(
        st.session_state.staking_data_optimistic["incentive_for_stakers_0"],
        label="Optimistic",
        color="green",
    )
    ax_3.plot(
        st.session_state.staking_data_pessimistic["incentive_for_stakers_0"],
        label="Pessimistic",
        color="red",
    )
    ax_3.set_title("Monthly incentive distribution for stakers")
    ax_3.set_xlabel("Time (Months)")
    ax_3.set_ylabel("Ioty")
    ax_3.ticklabel_format(style="plain", axis="y")
    ax_3.legend()
    ax_3.grid(False)
    st.pyplot(fig_3)

elif "Minting":
    initial_treasury_tokens = 3_000_000_000 * 0.15
    initial_staking_tokens = 3_000_000_000 * 0.3
    initial_minting_tokens = 3_000_000_000 * 0.15

    ratios = {"Treasury": 0.2, "Staking": 0.4, "Minting": 0.4}
    treasury_ratio = st.number_input(
        "Treasury redirection ratio",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        value=0.2,
    )
    staking_ratio = st.number_input(
        "Staking redirection ratio",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        value=0.4,
    )
    minting_ratio = st.number_input(
        "Minting redirection ratio",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        value=0.4,
    )
    st.write(
        f"the sum of the ratios is : {treasury_ratio + staking_ratio + minting_ratio}"
    )

    emission_rate = st.number_input(
        "Emission Constant of the minting pool",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        value=0.1,
    )
    pessimistic_pools = compute_distribution_scenario(
        "pessimistic", emission_rate, ratios
    )
    pessimistic_pools_data = pd.DataFrame(
        pool.tokens_history for pool in pessimistic_pools.values()
    ).T
    pessimistic_pools_data.columns = pessimistic_pools.keys()
    st.write("Pessimistic Scenario")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        pessimistic_pools_data["Staking"],
        label="Staking",
        color="blue",
    )
    ax.plot(
        pessimistic_pools_data["Treasury"],
        label="Treasury",
        color="green",
    )
    ax.plot(
        pessimistic_pools_data["Minting"],
        label="Minting",
        color="red",
    )
    ax.set_title("Percentage of tokens to be staked over the total supply")
    ax.set_xlabel("Time (Months)")
    ax.set_ylabel("% supply")
    ax.ticklabel_format(style="plain", axis="y")
    ax.legend()
    ax.grid(False)
    st.pyplot(fig)

    moderate_pools = compute_distribution_scenario("moderate", emission_rate, ratios)
    moderate_pools_data = pd.DataFrame(
        pool.tokens_history for pool in moderate_pools.values()
    ).T
    moderate_pools_data.columns = moderate_pools.keys()
    st.write("Moderate Scenario")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        moderate_pools_data["Staking"],
        label="Staking",
        color="blue",
    )
    ax.plot(
        moderate_pools_data["Treasury"],
        label="Treasury",
        color="green",
    )
    ax.plot(
        moderate_pools_data["Minting"],
        label="Minting",
        color="red",
    )
    ax.set_title("Percentage of tokens to be staked over the total supply")
    ax.set_xlabel("Time (Months)")
    ax.set_ylabel("% supply")
    ax.ticklabel_format(style="plain", axis="y")
    ax.legend()
    ax.grid(False)
    st.pyplot(fig)

    optimistic_pools = compute_distribution_scenario(
        "optimistic", emission_rate, ratios
    )
    optimistic_pools_data = pd.DataFrame(
        pool.tokens_history for pool in optimistic_pools.values()
    ).T
    optimistic_pools_data.columns = optimistic_pools.keys()
    st.write("Optimistic Scenario")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        optimistic_pools_data["Staking"],
        label="Staking",
        color="blue",
    )
    ax.plot(
        optimistic_pools_data["Treasury"],
        label="Treasury",
        color="green",
    )
    ax.plot(
        optimistic_pools_data["Minting"],
        label="Minting",
        color="red",
    )
    ax.set_title("Percentage of tokens to be staked over the total supply")
    ax.set_xlabel("Time (Months)")
    ax.set_ylabel("% supply")
    ax.ticklabel_format(style="plain", axis="y")
    ax.legend()
    ax.grid(False)
    st.pyplot(fig)
