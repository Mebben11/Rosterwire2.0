'use client';
import React, { useEffect, useState, useMemo } from 'react';
import { useTable, useSortBy } from 'react-table';
import styles from '../styles/PlayersTable.module.css';

export default function Home() {
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState('');

  // Fetch teams on mount
useEffect(() => {
  fetch('http://localhost:5000/api/teams')
    .then(res => res.json())
    .then(data => {
      console.log('Teams loaded:', data.teams);
      setTeams(data.teams || []);
    })
    .catch(err => {
      console.error('Failed to fetch teams:', err);
      setTeams([]);  // fallback to empty
    });
}, []);

  // Fetch players when a team is selected
  useEffect(() => {
    if (!selectedTeam) {
      setPlayers([]);
      return;
    }

    setLoading(true);
    fetch(`http://localhost:5000/api/players/team/${selectedTeam}`)
      .then(res => res.json())
      .then(data => {
        setPlayers(data.players || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch players:', err);
        setLoading(false);
      });
  }, [selectedTeam]);

  const columns = useMemo(() => [
    { Header: 'Name', accessor: 'name' },
    {
      Header: 'Team',
      accessor: row => row.team.abbreviation || 'N/A',
      id: 'team',
    },
    {
      Header: '⭐',
      accessor: 'star_value',
      Cell: ({ value }) =>
        value
          ? '★'.repeat(Math.round(value)) + '☆'.repeat(5 - Math.round(value))
          : '☆☆☆☆☆',
    },
    {
      Header: 'PTS',
      accessor: row => row.last_season_stats.PTS || 0,
      id: 'pts',
    },
    {
      Header: 'REB',
      accessor: row => row.last_season_stats.REB || 0,
      id: 'reb',
    },
    {
      Header: 'AST',
      accessor: row => row.last_season_stats.AST || 0,
      id: 'ast',
    },
  ], []);

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
  } = useTable({ columns, data: players }, useSortBy);

  return (
    <div className={styles.wrapper} style={{ textAlign: 'center' }}>
      <h1 className={styles.title}>Rosterwire</h1>

      <div className={styles.filterContainer} style={{ marginBottom: '1rem' }}>
        <label htmlFor="team-select" style={{ color: 'white', marginRight: '0.5rem' }}>
          Select Team:
        </label>
        <select
          id="team-select"
          value={selectedTeam}
          onChange={e => setSelectedTeam(e.target.value)}
          style={{ padding: '0.3rem 0.5rem', fontSize: '1rem' }}
        >
          <option value="">-- Select a Team --</option>
          {teams.map(team => (
            <option key={team.id} value={team.abbreviation}>
              {team.full_name} ({team.abbreviation})
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className={styles.loading}>Loading NBA players...</div>
      ) : (
        <table {...getTableProps()} className={styles.table} style={{ margin: '0 auto' }}>
          <thead>
            {headerGroups.map(group => (
              <tr {...group.getHeaderGroupProps()} key={group.id}>
                {group.headers.map(column => (
                  <th
                    {...column.getHeaderProps(column.getSortByToggleProps())}
                    key={column.id}
                    className={styles.header}
                  >
                    {column.render('Header')}
                    <span>
                      {column.isSorted ? (column.isSortedDesc ? ' 🔽' : ' 🔼') : ''}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody {...getTableBodyProps()}>
            {rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} style={{ textAlign: 'center', color: 'white' }}>
                  No players found for this team.
                </td>
              </tr>
            )}
            {rows.map(row => {
              prepareRow(row);
              return (
                <tr {...row.getRowProps()} key={row.id} className={styles.row}>
                  {row.cells.map(cell => (
                    <td {...cell.getCellProps()} key={cell.column.id} className={styles.cell}>
                      {cell.render('Cell')}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
