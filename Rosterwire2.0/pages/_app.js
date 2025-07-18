import '../styles/globals.css';
import '../styles/TransactionsTable.module.css';
import Sidebar from '../components/Sidebar';

export default function App({ Component, pageProps }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Component {...pageProps} />
      </main>
    </div>
  );
}
