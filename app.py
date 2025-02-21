import streamlit as st
from scraper import MedicalPaperScraper
from rag_system import MedicalRAG
import schedule
from datetime import datetime

def initialize_system():
    sources = [
        "https://pubmed.ncbi.nlm.nih.gov/?term=latest",
        # Add more sources as needed
    ]
    
    scraper = MedicalPaperScraper(sources)
    rag = MedicalRAG()
    return scraper, rag

def update_papers():
    st.session_state.last_update = datetime.now()
    papers = st.session_state.scraper.run_scraper()
    st.session_state.rag.process_papers(papers)
    st.success(f"Database updated at {st.session_state.last_update}")

def main():
    st.title("Medical Research Papers RAG System")
    
    if 'initialized' not in st.session_state:
        st.session_state.scraper, st.session_state.rag = initialize_system()
        st.session_state.initialized = True
        st.session_state.last_update = datetime.now()
        
        # Schedule updates every 24 hours
        schedule.every(24).hours.do(update_papers)

    st.sidebar.title("Controls")
    if st.sidebar.button("Update Database"):
        update_papers()

    st.sidebar.write(f"Last Update: {st.session_state.last_update}")

    query = st.text_input("Enter your medical research query:")
    if query:
        with st.spinner("Analyzing research papers..."):
            response = st.session_state.rag.query_papers(query)
            
            # Split the response to separate the analysis and referenced papers
            parts = response.split("5. Referenced Papers")
            if len(parts) > 1:
                analysis = parts[0]
                referenced_papers = parts[1]
                
                # Display the analysis
                st.write(analysis)
                
                # Display referenced papers with links
                st.subheader("Referenced Papers:")
                paper_titles = [title.strip() for title in referenced_papers.split('\n') if title.strip()]
                
                for title in paper_titles:
                    if title in st.session_state.rag.paper_urls:
                        url = st.session_state.rag.paper_urls[title]
                        st.markdown(f"- [{title}]({url})")
                    else:
                        st.markdown(f"- {title}")
            else:
                st.write(response)

    # Run scheduled tasks
    schedule.run_pending()

if __name__ == "__main__":
    main()