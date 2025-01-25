import React, { useEffect, useState } from 'react';
import axios from 'axios';

const App: React.FC = () => {
    const [message, setMessage] = useState('Loading...');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        axios.get('http://127.0.0.1:5001/api/hello')
            .then(response => {
                setMessage(response.data.message);
                setError(null);
            })
            .catch(error => {
                console.error('There was an error!', error);
                setError('Failed to fetch data from server');
            });
    }, []);

    useEffect(() => {
      axios.get('http://127.0.0.1:5001/api/bye')
          .then(response => {
              setMessage(response.data.message);
              setError(null);
          })
          .catch(error => {
              console.error('There was an error!', error);
              setError('Failed to fetch data from server');
          });
  }, []);

    return (
        <div className="App">
            <header className="App-header">
                <h1>Welcome to My App</h1>
                {error ? (
                    <p style={{ color: 'red' }}>{error}</p>
                ) : (
                    <p>{message}</p>
                )}
            </header>
        </div>
    );
}

export default App;