import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def assign_categories(df_raw):
    category = None
    categories = []

    for _, row in df_raw.iterrows():
        nomenclature = str(row.get('Nomenclature', '')).strip()
        bom_qty = str(row.get("Bom Qty", "")).strip()

        # If Bom Qty is missing or not numeric, it's a category heading
        if not bom_qty.replace("-", "").replace(" ", "").isnumeric():
            category = nomenclature.upper()
            categories.append(None)  # Don't assign the heading row itself
        else:
            categories.append(category)

    df_raw["Category"] = categories
    return df_raw
    
st.set_page_config(page_title="Component Availability Dashboard", layout="wide")
st.title("🛠️ Component Test & Availability Dashboard")

uploaded_file = st.file_uploader("Upload your Excel or CSV file", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)

    df_raw.columns = df_raw.columns.str.strip().str.title()
    st.write("Column names after cleanup:", df_raw.columns.tolist())

    df_raw = assign_categories(df_raw)  # Add Category column
    df = df_raw.copy()

    with st.sidebar:
        st.header("🔎 Filter Options")
        selected_section = st.selectbox("Filter by Section", ["All"] + sorted(df["Section"].dropna().unique().tolist()))
        selected_category = st.selectbox("Filter by Category", ["All"] + sorted(df["Category"].dropna().unique().tolist()))
        
        # Add filter by System Type (like 11(A/I/F))
        test_cols = [col for col in df.columns if "(A/I/F)" in col]
        selected_system = st.selectbox("Filter by System Type", ["All"] + test_cols)
    
    # Apply filters
    if selected_section != "All":
        df = df[df["Section"] == selected_section]

    # Apply System Type filter
    if selected_system != "All":
        df = df[df[selected_system] == "A"]

    if selected_category != "All":
        df = df[df["Category"] == selected_category]

    # Optional: Remove heading rows (where Nomenclature is one of the known headings)
    # Remove any row where Bom Qty is not a number (i.e., category headings)
    df = df[pd.to_numeric(df["Bom Qty"], errors="coerce").notna()]

    # Convert "Available Up To" from "AP 25" to just 25
    df["Available Up To"] = (
        pd.to_numeric(
            df["Available Up To"].astype(str).str.extract(r"(\d+)", expand=False),
            errors="coerce"
        )
    )

    st.subheader("Preview of Cleaned Data")
    st.dataframe(df[["Section", "Category", "Nomenclature", "Bom Qty", "Stock"]].head(100))

    # Test stage columns
    test_columns = [col for col in df.columns if "(A/I/F)" in col]

    # Count how many system types each component is available in
    df["Available In"] = df[test_columns].apply(lambda row: (row == "A").sum(), axis=1)

    all_system = df[df["Available In"] == len(test_columns)]
    none_system = df[df["Available In"] == 0]
    
    colA, colB, colC, colD = st.columns(4)
    colA.metric("📦 Total Components", len(df))
    colB.metric("🔁 Avg Used In Systems", f"{df['Available In'].mean():.2f}")
    colC.metric("✅ Used in All Systems", len(all_system))
    colD.metric("❌ Used in None", len(none_system))

    # Components used in all system types
    st.subheader("✅ Components Used in All System Types")
    st.dataframe(all_system[["Nomenclature", "Available In"]])

    # Components not used in any system types
    st.subheader("❌ Components Not Used in Any System Type")
    st.dataframe(none_system[["Nomenclature", "Available In"]])

    # Show top 10 components used in most system types
    top_multiuse = df.sort_values("Available In", ascending=False).head(10)
    st.subheader("Top 10 Components Used in Most System Types")
    st.dataframe(top_multiuse[["Nomenclature", "Available In"]])

    # Count of 'S' and 'A' across all test columns
    st.subheader("Component Test Stage Summary")
    status_counts = pd.DataFrame()

    status_counts["Component"] = df["Nomenclature"]
    status_counts["Short Count"] = df[test_columns].apply(lambda row: (row == "S").sum(), axis=1)
    status_counts["Available Count"] = df[test_columns].apply(lambda row: (row == "A").sum(), axis=1)

    top_short = status_counts.sort_values("Short Count", ascending=False).head(10)
    top_available = status_counts.sort_values("Available Count", ascending=False).head(10)

    col1, col2 = st.columns(2)

    with col1:
        st.write("Top 10 Shortage Components (Most 'S')")
        st.dataframe(top_short)

    with col2:
        st.write("Top 10 Available Components (Most 'A')")
        st.dataframe(top_available)

    # System-wise Availability vs Shortage Summary
    system_availability = pd.DataFrame({
        "Available": (df[test_columns] == "A").sum(),
        "Short": (df[test_columns] == "S").sum()
    })

    st.subheader("System-Wise Component Availability Summary")
    fig_system, ax_system = plt.subplots(figsize=(7, 4), dpi=100)
    system_availability.plot(kind="bar", ax=ax_system)
    ax_system.set_ylabel("Component Count")
    ax_system.set_title("Per System Type Availability vs Shortage")
    st.pyplot(fig_system, use_container_width=False)

    # Pie chart of total 'A' vs 'S'
    total_A = (df[test_columns] == "A").sum().sum()
    total_S = (df[test_columns] == "S").sum().sum()

    st.subheader("Overall Test Stage Status Distribution")
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.pie([total_A, total_S], labels=["Available (A)", "Short (S)"], autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    st.pyplot(fig, use_container_width=False)

    # Bar chart: Average 'Available Up To' by Section
    if "Section" in df.columns:
        st.subheader("Average 'Available Up To' per Section")
        section_availability = df.groupby("Section")[df.columns[df.columns.str.lower() == "available up to"].tolist()[0]].mean()
        fig2, ax2 = plt.subplots(figsize=(5.5, 3.5), dpi=100)
        section_availability.plot(kind="bar", ax=ax2)
        ax2.set_ylabel("Average Stage Available")
        ax2.set_title("Component Readiness by Section")
        st.pyplot(fig2, use_container_width=False)

    # Bar chart: Average 'Available Up To' by Category
    if "Category" in df.columns:
        st.subheader("Average 'Available Up To' by Category")
        category_availability = df.groupby("Category")["Available Up To"].mean().sort_values()
        fig3, ax3 = plt.subplots(figsize=(6, 4), dpi=100)
        category_availability.plot(kind="bar", ax=ax3)
        ax3.set_ylabel("Average Stage Available")
        ax3.set_title("Component Readiness by Category")
        st.pyplot(fig3, use_container_width=False)

    # Heatmap of component availability across system types
    st.subheader("🧊 Component-System Availability Heatmap")

    heatmap_data = df.set_index("Nomenclature")[test_columns]
    heatmap_data = heatmap_data.replace({"A": 1, "S": 0, "": None})

    fig_hm, ax_hm = plt.subplots(figsize=(10, len(heatmap_data) * 0.3), dpi=100)
    im = ax_hm.imshow(heatmap_data, aspect="auto", cmap="Greens", interpolation="nearest")

    ax_hm.set_xticks(range(len(test_columns)))
    ax_hm.set_xticklabels(test_columns, rotation=45)
    ax_hm.set_yticks(range(len(heatmap_data)))
    ax_hm.set_yticklabels(heatmap_data.index)
    ax_hm.set_title("Availability Heatmap (Green = Available)")

    plt.colorbar(im, ax=ax_hm)
    st.pyplot(fig_hm, use_container_width=True)

    # Identify components with critical issues (e.g., no stock or unused in any system)
    critical_components = df[(df["Stock"] == 0) | (df["Available In"] == 0)]

    if not critical_components.empty:
        st.subheader("🚨 Critical Components (Zero Stock or Not Used Anywhere)")
        st.dataframe(critical_components[["Nomenclature", "Stock", "Available In"]])
    else:
        st.subheader("✅ No Critical Components Found")

    # Allow user to download filtered final dataset
    st.download_button("📥 Download Filtered Data as CSV", df.to_csv(index=False), file_name="filtered_components.csv")
    
    st.success("Analysis complete!")
else:
    st.info("👈 Please upload your Excel file to begin.")
