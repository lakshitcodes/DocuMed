import streamlit as st
from scraper import MedicalPaperScraper
from rag_system import MedicalRAG
import schedule
from datetime import datetime, timedelta
import time
import threading
import json
import os

def initialize_system():
    sources = [
        "https://pubmed.ncbi.nlm.nih.gov/?term=latest",
        "https://www.biorxiv.org/collection/new_results",
        "https://www.medrxiv.org/content/early/recent",
        "https://www.sciencedirect.com/browse/journals-and-books?subject=medicine",
        "https://trialsearch.who.int/trial-search",
        "https://europepmc.org/search?query=recent"
    ]
    
    scraper = MedicalPaperScraper(sources)
    rag = MedicalRAG()
    return scraper, rag

def update_papers():
    """Update papers and return the newly fetched papers"""
    papers = st.session_state.scraper.run_scraper()
    st.session_state.rag.process_papers(papers)
    st.session_state.last_update = datetime.now()
    st.session_state.next_update = datetime.now() + timedelta(hours=12)
    st.session_state.recent_papers = papers[:10]  # Keep most recent 10 papers
    
    # Save update time to file
    with open('last_update.json', 'w') as f:
        json.dump({
            'last_update': st.session_state.last_update.isoformat(),
            'next_update': st.session_state.next_update.isoformat()
        }, f)

def run_scheduler():
    """Background scheduler to run updates"""
    while True:
        schedule.run_pending()
        time.sleep(60)

def display_recent_papers():
    """Display the most recently fetched papers"""
    st.subheader("Recently Added Papers")
    for paper in st.session_state.recent_papers:
        with st.expander(f"{paper['title']} ({paper['source']})"):
            st.write(f"**Date:** {paper['date']}")
            st.write(f"**Abstract:** {paper['abstract'][:200]}...")
            st.write(f"**Source:** [{paper['source']}]({paper['url']})")

def display_all_papers():
    """Display all stored papers with filtering options"""
    st.subheader("All Stored Papers")
    
    # Get all JSON files from backup directory
    backup_dir = os.getenv('BACKUP_DIR', './paper_backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    json_files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
    
    if not json_files:
        st.warning("No paper backups found yet. Please update the database.")
        return
        
    # Load the most recent backup
    latest_backup = max(json_files)
    with open(os.path.join(backup_dir, latest_backup), 'r') as f:
        all_papers = json.load(f)
    
    # Filtering options
    col1, col2 = st.columns(2)
    with col1:
        sources = list(set(paper['source'] for paper in all_papers))
        selected_source = st.multiselect('Filter by source:', sources)
    
    with col2:
        sort_by = st.selectbox('Sort by:', ['date', 'source', 'title'])
    
    # Filter papers
    if selected_source:
        filtered_papers = [p for p in all_papers if p['source'] in selected_source]
    else:
        filtered_papers = all_papers
    
    # Sort papers
    if sort_by == 'date':
        filtered_papers = sorted(filtered_papers, key=lambda x: x['date'], reverse=True)
    elif sort_by == 'source':
        filtered_papers = sorted(filtered_papers, key=lambda x: x['source'])
    else:
        filtered_papers = sorted(filtered_papers, key=lambda x: x['title'])
    
    # Display papers
    st.write(f"Showing {len(filtered_papers)} papers")
    for i, paper in enumerate(filtered_papers):
        with st.expander(f"{paper['title']} - {paper['source']} ({paper['date']})"):
            st.write(f"**Abstract:**\n{paper['abstract']}")
            unique_key = f"btn_{i}_{int(time.time())}_{paper['source']}"
            if st.button(f"Open Paper", key=unique_key):
                st.markdown(f"<a href='{paper['url']}' target='_blank'>Click here to open paper</a>", unsafe_allow_html=True)

def display_search_results(query_result):
    """Display search results in a structured format"""
    if not query_result:
        st.warning("No results found.")
        return

    # Display analysis in a cleaner format
    analysis_text = query_result['analysis']
    
    # Split the analysis into sections
    sections = analysis_text.split('\n')
    current_section = ""
    
    for section in sections:
        if section.startswith('1. Key Findings'):
            st.markdown("### 🔍 Key Findings")
            current_section = "key_findings"
        elif section.startswith('2. Clinical Implications'):
            st.markdown("### 👨‍⚕️ Clinical Implications")
            current_section = "implications"
        elif section.startswith('3. Critical Analysis'):
            st.markdown("### 📊 Critical Analysis")
            current_section = "analysis"
        elif section.startswith('4. Recommendations'):
            st.markdown("### 💡 Recommendations")
            current_section = "recommendations"
        elif section.strip():  # Only add non-empty lines
            st.write(section)

    # Display referenced papers
    papers = query_result.get('papers', [])
    if papers:
        st.markdown("### 📚 Referenced Papers")
        
        for i, paper in enumerate(papers):
            with st.expander(f"{i+1}. {paper['title']}", expanded=True):
                st.markdown(f"**Source:** {paper['source']}")
                st.markdown(f"**Date:** {paper['date']}")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("Open Paper", key=f"ref_{i}_{int(time.time())}"):
                        st.markdown(f"<a href='{paper['url']}' target='_blank'>Opening paper...</a>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"[View Original Paper]({paper['url']})")
    else:
        st.info("No specific papers were referenced for this query.")

def main():
    st.title("Medical Research Papers RAG System")
    
    # Initialize system state
    if 'initialized' not in st.session_state:
        st.session_state.scraper, st.session_state.rag = initialize_system()
        st.session_state.initialized = True
        
        # Try to load last update time
        if os.path.exists('last_update.json'):
            with open('last_update.json', 'r') as f:
                data = json.load(f)
                st.session_state.last_update = datetime.fromisoformat(data['last_update'])
                st.session_state.next_update = datetime.fromisoformat(data['next_update'])
        else:
            st.session_state.last_update = None
            st.session_state.next_update = None
        
        # Initialize recent papers list
        st.session_state.recent_papers = []
        
        # Schedule updates every 12 hours
        schedule.every(12).hours.do(update_papers)
        
        # Start the scheduler in a background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

    # Navigation
    page = st.sidebar.radio("Navigation", ["Recent Updates", "All Papers", "Search"])
    
    # Display update status in sidebar
    st.sidebar.title("Update Status")
    if st.session_state.last_update:
        st.sidebar.write(f"Last Update: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M')}")
        st.sidebar.write(f"Next Update: {st.session_state.next_update.strftime('%Y-%m-%d %H:%M')}")
    
    # Manual update button
    if st.sidebar.button("Update Now"):
        with st.spinner("Fetching latest papers..."):
            update_papers()
        st.success("Database updated successfully!")

    # Content based on navigation selection
    if page == "Recent Updates":
        if st.session_state.recent_papers:
            display_recent_papers()
        elif not st.session_state.last_update:
            st.warning("No papers fetched yet. Click 'Update Now' to fetch the latest papers.")
    
    elif page == "All Papers":
        display_all_papers()
    
    else:  # Search page
        st.subheader("Search and Analysis")
        query = st.text_input("Enter your medical research query:")
        if query:
            with st.spinner("Analyzing research papers..."):
                results = st.session_state.rag.query_papers(query)
                display_search_results(results)

if __name__ == "__main__":
    main()