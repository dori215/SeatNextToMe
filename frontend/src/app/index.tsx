import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, Alert } from 'react-native';
import API from '../api/axios'; // Asigură-te că calea spre fișierul tău de axios este corectă

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Eroare', 'Te rog completează emailul și parola!');
      return;
    }

    try {
      setLoading(true);

      // Backend-ul cere datele sub formă de URL-encoded form pentru login
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await API.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      // Dacă totul e ok, primim un access_token
      const token = response.data.access_token;
      console.log('Token primit:', token);

      Alert.alert('Succes!', 'Te-ai conectat cu succes în SeatNextToMe!');
      
      // Aici poți salva token-ul (de ex. în memorie sau AsyncStorage) 
      // și să redirecționezi userul către ecranul principal cu evenimente.

    } catch (err) {
      console.error(err);
      Alert.alert('Eroare de autentificare', 'Email sau parolă incorecte.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>SeatNextToMe 🎸</Text>
      <Text style={styles.subtitle}>Conectează-te pentru a găsi parteneri de evenimente</Text>

      <View style={styles.form}>
        <TextInput
          style={styles.input}
          placeholder="Email (ex: ana@demo.ro)"
          placeholderTextColor="#888"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />

        <TextInput
          style={styles.input}
          placeholder="Parolă"
          placeholderTextColor="#888"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        <TouchableOpacity 
          style={styles.button} 
          onPress={handleLogin}
          disabled={loading}
        >
          <Text style={styles.buttonText}>
            {loading ? 'Se conectează...' : 'Autentificare'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#f8f9fa',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#111',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 32,
  },
  form: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    paddingHorizontal: 16,
    marginBottom: 16,
    fontSize: 15,
    backgroundColor: '#f9fafb',
    color: '#000',
  },
  button: {
    backgroundColor: '#6366f1',
    height: 50,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
});