import styles from '../styles/StarRating.module.css';

export default function StarRating({ rating }) {
  return (
    <div className={styles.starRating}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={i <= rating ? styles.filled : styles.empty}>★</span>
      ))}
    </div>
  );
}
