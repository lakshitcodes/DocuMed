from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

class MedicalRAG:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="mixtral-8x7b-32768"
        )
        self.vectorstore = None

    def process_papers(self, papers: List[Dict]):
        texts = []
        metadata_list = []
        
        for paper in papers:
            # Store complete paper info in metadata
            metadata = {
                'title': paper['title'],
                'url': paper['url'],
                'source': paper['source'],
                'date': paper['date']
            }
            
            text = f"Title: {paper['title']}\nAbstract: {paper['abstract']}\nDate: {paper['date']}\nSource: {paper['source']}\nURL: {paper['url']}"
            chunks = self.text_splitter.split_text(text)
            
            for chunk in chunks:
                texts.append(chunk)
                metadata_list.append(metadata)

        if not self.vectorstore:
            self.vectorstore = Chroma.from_texts(
                texts,
                self.embeddings,
                metadatas=metadata_list,
                persist_directory="./chroma_db"
            )
        else:
            self.vectorstore.add_texts(texts, metadatas=metadata_list)

        if not self.vectorstore:
            self.vectorstore = Chroma.from_texts(
                texts,
                self.embeddings,
                persist_directory="./chroma_db"
            )
        else:
            self.vectorstore.add_texts(texts)

    def query_papers(self, query: str) -> Dict:
        if not self.vectorstore:
            return {
                'analysis': "No papers have been processed yet. Please update the database first.",
                'papers': []
            }
            
        # First get relevant documents
        docs = self.vectorstore.similarity_search(query, k=5)
        
        # Extract document texts for the analysis
        texts = [doc.page_content for doc in docs]
        context = "\n\n".join(texts)
        
        # Prepare the prompt
        template = """You are a medical research assistant analyzing academic papers. Given the following research papers, 
        provide a detailed analysis focusing on the practical implications and key takeaways.

        Research papers: {context}

        Question: {question}

        Follow this structure in your response:
        1. Key Findings (focus on the most significant and well-supported conclusions)
        2. Clinical Implications (specific, actionable insights for medical professionals)
        3. Critical Analysis (evaluate the strength of evidence and any limitations)
        4. Recommendations (concrete, evidence-based suggestions)

        Be specific and factual. Focus on well-supported conclusions and clearly indicate any uncertainty.
        Include numerical data and statistics when available.
        """

        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        # Create and run the chain
        chain = prompt | self.llm
        analysis = chain.invoke({"context": context, "question": query})
        
        # Extract the content from the response object
        if hasattr(analysis, 'content'):
            analysis_text = analysis.content
        else:
            analysis_text = str(analysis)

        # Extract metadata from retrieved documents
        referenced_papers = []
        for doc in docs:
            if hasattr(doc, 'metadata'):
                paper_info = doc.metadata
                if paper_info:  # Only add if we have metadata
                    referenced_papers.append({
                        'title': paper_info.get('title', 'Unknown Title'),
                        'url': paper_info.get('url', '#'),
                        'source': paper_info.get('source', 'Unknown Source'),
                        'date': paper_info.get('date', 'Unknown Date')
                    })
        
        return {
            'analysis': analysis_text,
            'papers': referenced_papers
        }