import streamlit as st
import pandas as pd
from pyairtable import Api
import plotly.express as px
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Airtable configuration
API_KEY = 'patnV7vPekY6JDuWY.84ed211a9ed400c9b9a11d63259332eecbfb873761ff8ba43afa99d5196933fa'
BASE_ID = 'appqm2qncCq5nX5eu'
TABLE_NAME = 'Orders'

# Initialize Airtable API
api = Api(API_KEY)
table = api.table(BASE_ID, TABLE_NAME)


def load_data():
    """Load data from Airtable and convert to DataFrame"""
    records = table.all()
    data = []
    for record in records:
        fields = record['fields']
        fields['record_id'] = record['id']
        
        # Convert Order Amount to numeric if it exists
        if 'Order Amount' in fields:
            try:
                amount = fields['Order Amount']
                # Handle if amount is a list
                if isinstance(amount, list):
                    amount = amount[0]  # Take the first value if it's a list
                
                # Handle string values with commas and currency symbols
                if isinstance(amount, str):
                    # Remove currency symbols, spaces, and commas
                    amount_str = amount.replace('$', '').replace(',', '').strip()
                    fields['Order Amount'] = float(amount_str)
                else:
                    fields['Order Amount'] = float(amount)
                
                # Round to remove decimals (optional - remove if you want to keep decimals)
                fields['Order Amount'] = round(fields['Order Amount'])
                
            except (ValueError, TypeError, AttributeError, IndexError) as e:
                print(f"Failed to convert Order Amount: {fields['Order Amount']} - Error: {str(e)}")
                fields['Order Amount'] = 0.0
        
        # Convert Shipped by to string if it's a list
        if 'Shipped by' in fields:
            if isinstance(fields['Shipped by'], list):
                fields['Shipped by'] = ', '.join(fields['Shipped by'])
                
        data.append(fields)
    
    df = pd.DataFrame(data)
    
    # Convert date column
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        
    # Ensure Order Amount is numeric
    if 'Order Amount' in df.columns:
        df['Order Amount'] = pd.to_numeric(df['Order Amount'], errors='coerce').fillna(0)
        
    return df


def show_order_details(df, search_id):
    """Display details for a specific order"""
    # Clean up search input and data for comparison
    search_id = str(search_id).replace(',', '').strip()
    
    # Create search condition based on available columns
    search_condition = df['ID'].astype(str).str.replace(',', '').str.strip() == search_id
    
    # Add Shopify ID condition only if the column exists
    if 'Shopify ID' in df.columns:
        search_condition |= df['Shopify ID'].astype(str).str.replace(',', '').str.strip() == search_id
    
    order = df[search_condition]
    
    if not order.empty:
        st.write("### Order Details")
        
        # Display order information in columns
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Order ID:**", order['ID'].iloc[0])
            if 'Shopify ID' in order.columns:
                st.write("**Shopify ID:**", order['Shopify ID'].iloc[0])
            st.write("**Date:**", order['Date'].iloc[0].strftime('%Y-%m-%d'))
            st.write("**Status:**", order['Order Status'].iloc[0])
            st.write("**Amount:**", f"${order['Order Amount'].iloc[0]:,.2f}")
        
        # ... rest of the function remains the same ...

        
        with col2:
            if 'Picker' in order.columns:
                st.write("**Picker:**", order['Picker'].iloc[0] if pd.notna(order['Picker'].iloc[0]) else 'N/A')
            if 'Shipped by' in order.columns:
                st.write("**Shipped by:**", order['Shipped by'].iloc[0] if pd.notna(order['Shipped by'].iloc[0]) else 'N/A')
        
        # Show all other fields in a table
        st.write("### All Order Data")
        st.dataframe(order.transpose())
    else:
        st.error(f"Order not found with ID: {search_id}")

def show_orders_page(df):
    """Display the orders search page"""
    st.title("🔍 Order Search")
    
    # Search box with placeholder text
    search_id = st.text_input(
        "Enter Order ID or Shopify ID",
        placeholder="Enter ID and press Enter"
    )
    
    if search_id:
        show_order_details(df, search_id)
    
    # Show recent orders in a table with search
    st.write("### Recent Orders")
    # Display most recent 100 orders by default
    recent_df = df.sort_values('Date', ascending=False).head(100)
    st.dataframe(recent_df, use_container_width=True)
# ... rest of the code remains the same ...

def main():
    st.set_page_config(page_title="Derhali Dashboard", layout="wide")
    
    # Load data
    with st.spinner("Loading data from Airtable..."):
        df = load_data()
    
    # Navigation
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'
    
    # Navigation buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Dashboard", use_container_width=True):
            st.session_state.current_page = 'dashboard'
    with col2:
        if st.button("Orders", use_container_width=True):
            st.session_state.current_page = 'orders'
    
    # Display current page
    if st.session_state.current_page == 'orders':
        show_orders_page(df)
    else:
        # Header
        st.title("📊 Derhali Dashboard")
    
    # Store column data types in session state for debugging (hidden from UI)
    if 'debug_info' not in st.session_state:
        st.session_state.debug_info = {
            'column_types': df.dtypes.to_dict(),
            'columns': df.columns.tolist()
        }
    
    # Date Filter Section
    st.sidebar.header("Date Filter")
    if 'Date' not in df.columns:
        st.error("Date column not found in the data")
        return
        
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
    
    # ... rest of the code remains the same ...
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", 
                                 min_date,
                                 min_value=min_date,
                                 max_value=max_date)
    with col2:
        end_date = st.date_input("End Date", 
                               max_date,
                               min_value=min_date,
                               max_value=max_date)

    # Filter data based on date range
    mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)
    filtered_df = df.loc[mask]
    
    # Analytics Dashboard Layout
    col1, col2, col3, col4 = st.columns(4)
    
    # Key Metrics
    # Key Metrics
    with col1:
        total_orders = len(filtered_df)
        st.metric("Total Orders", f"{total_orders:d}")
    
    with col2:
        shipped_orders = len(filtered_df[filtered_df['Order Status'] == 'تم الشحن'])
        st.metric("Shipped Orders", f"{shipped_orders:d}")
    
    with col3:
        returned_orders = len(filtered_df[filtered_df['Order Status'] == 'مرتجع'])
        st.metric("Returned Orders", f"{returned_orders:d}")
    
    with col4:
        if 'Order Amount' in filtered_df.columns:
            total_revenue = filtered_df['Order Amount'].sum()
            st.metric("Total Revenue", f"${total_revenue:,.2f}")

    # Order Status Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Order Status Distribution")
        status_counts = filtered_df['Order Status'].value_counts()
        fig = px.pie(values=status_counts.values, 
                    names=status_counts.index, 
                    title="Order Status Distribution")
        st.plotly_chart(fig, use_container_width=True)
    
        # Shipping Analysis
    st.subheader("Shipping Analysis")
    
    # Group by Shipped by
    if 'Shipped by' in filtered_df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            shipper_stats = filtered_df.groupby('Shipped by').agg({
                'record_id': 'count',  # Changed from 'ID' to 'record_id'
                'Order Amount': 'sum'
            }).reset_index()
            shipper_stats.columns = ['Shipper', 'Order Count', 'Total Amount']
            
            fig = px.bar(shipper_stats, 
                        x='Shipper', 
                        y='Order Count',
                        title='Orders by Shipping Provider')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(shipper_stats, 
                        x='Shipper', 
                        y='Total Amount',
                        title='Revenue by Shipping Provider')
            st.plotly_chart(fig, use_container_width=True)

    # Picker Performance Analysis
    st.subheader("Picker Performance")
    if 'Picker' in filtered_df.columns:
        picker_df = filtered_df[filtered_df['Picker'].notna()]
        
        if not picker_df.empty:
            col1, col2 = st.columns(2)
            
            # Calculate picker statistics
            picker_stats = picker_df.groupby('Picker').agg({
                'record_id': 'count',
                'Order Amount': 'sum'
            }).reset_index()
            picker_stats.columns = ['Picker', 'Orders Processed', 'Total Amount']
            
            # Display picker order counts
            with col1:
                fig = px.bar(picker_stats,
                            x='Picker',
                            y='Orders Processed',
                            title='Orders Processed by Picker')
                st.plotly_chart(fig, use_container_width=True)
            
            # Display picker revenue
            with col2:
                fig = px.bar(picker_stats,
                            x='Picker',
                            y='Total Amount',
                            title='Revenue Processed by Picker')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No picker data available for the selected date range")

    # Download filtered data option
    st.sidebar.markdown("---")
    if st.sidebar.button("Download Filtered Data"):
        csv = filtered_df.to_csv(index=False)
        st.sidebar.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"orders_data_{start_date}_to_{end_date}.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()