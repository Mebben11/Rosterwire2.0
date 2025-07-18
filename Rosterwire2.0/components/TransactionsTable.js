import React, { useState } from 'react';
import styles from '../styles/TransactionsTable.module.css';

function capitalizeWords(str) {
  return str
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default function TransactionsTable({ transactions }) {
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;
  const totalPages = Math.ceil(transactions.length / itemsPerPage);

  const startIdx = (currentPage - 1) * itemsPerPage;
  const currentTransactions = transactions.slice(startIdx, startIdx + itemsPerPage);

  const goFirst = () => setCurrentPage(1);
  const goPrev = () => currentPage > 1 && setCurrentPage(currentPage - 1);
  const goNext = () => currentPage < totalPages && setCurrentPage(currentPage + 1);
  const goLast = () => setCurrentPage(totalPages);

  const fixedTableHeight = 48 * itemsPerPage + 56 + 30; 

  return (
    <div className={styles.container}>
      <table
        className={styles.table}
        style={{ minHeight: fixedTableHeight, display: 'block', overflowY: 'auto' }}
      >
        <thead>
          <tr>
            <th>Date</th>
            <th>Team</th>
            <th>Type</th>
            <th>Player</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {currentTransactions.length > 0 ? (
            currentTransactions.map((tx, idx) => {
              const playerName = capitalizeWords(tx.PLAYER_SLUG.replace(/-/g, ' '));
              const teamName = capitalizeWords(tx.TEAM_SLUG.replace(/-/g, ' '));
              return (
                <tr
                  key={startIdx + idx}
                  className={(startIdx + idx) % 2 === 0 ? styles.evenRow : styles.oddRow}
                >
                  <td>{new Date(tx.TRANSACTION_DATE).toLocaleDateString()}</td>
                  <td>{teamName}</td>
                  <td>{tx.Transaction_Type}</td>
                  <td>{playerName}</td>
                  <td>{tx.TRANSACTION_DESCRIPTION}</td>
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan={5} style={{ textAlign: 'center', padding: '1rem' }}>
                No transactions to display.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div className={styles.pagination}>
        <button
          className={styles.pageButton}
          onClick={goFirst}
          disabled={currentPage === 1}
          aria-label="First page"
        >
          « First
        </button>
        <button
          className={styles.pageButton}
          onClick={goPrev}
          disabled={currentPage === 1}
          aria-label="Previous page"
        >
          ← Prev
        </button>

        <span className={styles.pageInfo}>
          Page {currentPage} of {totalPages || 1}
        </span>

        <button
          className={styles.pageButton}
          onClick={goNext}
          disabled={currentPage === totalPages || totalPages === 0}
          aria-label="Next page"
        >
          Next →
        </button>
        <button
          className={styles.pageButton}
          onClick={goLast}
          disabled={currentPage === totalPages || totalPages === 0}
          aria-label="Last page"
        >
          Last »
        </button>
      </div>
    </div>
  );
}
