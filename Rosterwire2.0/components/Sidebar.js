import Link from 'next/link';
import styles from '../styles/Sidebar.module.css';

const Sidebar = () => {
  return (
    <div className={styles.sidebar}>
      <h2>Rosterwire</h2>
      <nav>
        <ul>
          <li><Link href="/">Rosters</Link></li>
          <li><Link href="/transactions">Transactions</Link></li>
        </ul>
      </nav>
    </div>
  );
};

export default Sidebar;
