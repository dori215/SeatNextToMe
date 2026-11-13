import axios from 'axios';

// Aici setăm adresa backend-ului făcut de colegul tău în Python
const API = axios.create({
  baseURL: 'http://127.0.0.1:8000',
});

export default API;