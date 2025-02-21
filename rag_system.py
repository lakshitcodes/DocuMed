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
        self.paper_urls = {}  # Store paper URLs with their titles
        for paper in papers:
            text = f"Title: {paper['title']}\nAbstract: {paper['abstract']}\nDate: {paper['date']}\nSource: {paper['source']}\nURL: {paper['url']}"
            self.paper_urls[paper['title']] = paper['url']
            chunks = self.text_splitter.split_text(text)
            texts.extend(chunks)

        if not self.vectorstore:
            self.vectorstore = Chroma.from_texts(
                texts,
                self.embeddings,
                persist_directory="./chroma_db"
            )
        else:
            self.vectorstore.add_texts(texts)

    def query_papers(self, query: str) -> str:
        if not self.vectorstore:
            return "No papers have been processed yet. Please update the database first."
            
        retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 5}
        )

        template = """You are a medical research assistant. Given the following research papers, 
        provide a comprehensive analysis and highlight key findings, complications, and implications 
        for medical professionals. At the end of your response, list the titles of all papers you referenced.

        Research papers: {context}

        Question: {question}

        Please structure your response with:
        1. Key Findings
        2. Clinical Implications
        3. Potential Complications
        4. Recommendations for Medical Professionals
        5. Referenced Papers (list only the titles of papers you specifically referenced in your analysis)
        """

        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt}
        )

        return qa_chain.run(query)