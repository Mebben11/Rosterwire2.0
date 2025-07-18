import { useEffect, useState } from 'react';
import TransactionsTable from '../components/TransactionsTable';
import styles from '../styles/TransactionsTable.module.css';

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('http://localhost:5000/api/transactions/nba-movement')
      .then(async (res) => {
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`HTTP ${res.status}: ${text}`);
        }
        return res.json();
      })
      .then(data => {
        console.log('Raw NBA Player Movement data:', data);
        const rows = data?.NBA_Player_Movement?.rows;
        if (!rows || !Array.isArray(rows)) {
          setError('No rows found in response');
          setTransactions([]);
          return;
        }
        setTransactions(rows);
      })
      .catch(err => {
        console.error('Error fetching transactions:', err);
        setError(err.message);
      });
  }, []);

  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Recent NBA Transactions</h1>
      {error && <p className={styles.error}>Error: {error}</p>}
      <TransactionsTable transactions={transactions} />
    </div>
  );
}
