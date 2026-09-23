const express = require('express');
const path = require('node:path');
const { randomUUID, timingSafeEqual } = require('node:crypto');
const { Pool } = require('pg');

const app = express();
const port = Number(process.env.PORT) || 3000;
const pool = process.env.DATABASE_URL ? new Pool({ connectionString: process.env.DATABASE_URL }) : null;
const allowedStatuses = new Set(['À préparer', 'En vente', 'Réservé', 'Vendu']);

app.disable('x-powered-by');
app.use(express.json({ limit: '1mb' }));

app.get('/api/health', async (_req, res) => {
  if (!pool) return res.status(503).json({ status: 'database_not_configured' });
  try {
    await pool.query('SELECT 1');
    res.json({ status: 'ok', service: 'KP Cars Stock Manager' });
  } catch (error) {
    console.error('Database health check failed:', error.message);
    res.status(503).json({ status: 'database_unavailable' });
  }
});

function requireConfigurationAndAuth(req, res, next) {
  const appUser = process.env.APP_USER || 'kp-cars';
  const appPassword = process.env.APP_PASSWORD;
  if (!pool || !appPassword) {
    return res.status(503).send('KP Cars is not fully configured yet.');
  }

  const header = req.get('authorization') || '';
  const match = header.match(/^Basic\s+(.+)$/i);
  if (match) {
    try {
      const decoded = Buffer.from(match[1], 'base64').toString('utf8');
      const separator = decoded.indexOf(':');
      const user = separator < 0 ? '' : decoded.slice(0, separator);
      const password = separator < 0 ? '' : decoded.slice(separator + 1);
      const actual = Buffer.from(`${user}:${password}`);
      const expected = Buffer.from(`${appUser}:${appPassword}`);
      if (actual.length === expected.length && timingSafeEqual(actual, expected)) return next();
    } catch {
      // Invalid Basic Auth values are handled by the same challenge below.
    }
  }
  res.set('WWW-Authenticate', 'Basic realm="KP Cars Stock", charset="UTF-8"');
  res.status(401).send('Authentication required.');
}

app.use(requireConfigurationAndAuth);
app.use(express.static(path.join(__dirname, 'public')));

function parseVehicle(input, id = randomUUID()) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Données véhicule invalides.');
  const make = String(input.make || '').trim();
  const model = String(input.model || '').trim();
  if (!make || !model || make.length > 50 || model.length > 60) throw new Error('Marque et modèle sont obligatoires.');
  if (input.id && !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(input.id)) throw new Error('Identifiant véhicule invalide.');
  const number = (value, field, max = Number.MAX_SAFE_INTEGER, integer = false) => {
    if (value === '' || value === null || value === undefined) return null;
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > max || (integer && !Number.isInteger(parsed))) throw new Error(`Valeur invalide : ${field}.`);
    return parsed;
  };
  const status = allowedStatuses.has(input.status) ? input.status : 'À préparer';
  const notes = String(input.notes || '').trim();
  if (notes.length > 500) throw new Error('Les notes ne peuvent pas dépasser 500 caractères.');
  return {
    id: input.id || id,
    make,
    model,
    year: number(input.year, 'année', 2100, true),
    mileage: number(input.mileage, 'kilométrage', Number.MAX_SAFE_INTEGER, true),
    buyPrice: number(input.buyPrice, 'prix d’achat') ?? 0,
    otherCosts: number(input.otherCosts, 'autres frais') ?? 0,
    resalePrice: number(input.resalePrice, 'prix de revente') ?? 0,
    status,
    notes
  };
}

function toClient(row) {
  return {
    id: row.id,
    make: row.make,
    model: row.model,
    year: row.year,
    mileage: row.mileage,
    buyPrice: Number(row.buy_price),
    otherCosts: Number(row.other_costs),
    resalePrice: Number(row.resale_price),
    status: row.status,
    notes: row.notes,
    updatedAt: new Date(row.updated_at).getTime()
  };
}

const selectColumns = 'id, make, model, year, mileage, buy_price, other_costs, resale_price, status, notes, updated_at';

app.get('/api/vehicles', async (_req, res, next) => {
  try {
    const { rows } = await pool.query(`SELECT ${selectColumns} FROM vehicles ORDER BY updated_at DESC`);
    res.json(rows.map(toClient));
  } catch (error) { next(error); }
});

app.post('/api/vehicles', async (req, res, next) => {
  try {
    const v = parseVehicle(req.body);
    const { rows } = await pool.query(
      `INSERT INTO vehicles (id, make, model, year, mileage, buy_price, other_costs, resale_price, status, notes)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING ${selectColumns}`,
      [v.id, v.make, v.model, v.year, v.mileage, v.buyPrice, v.otherCosts, v.resalePrice, v.status, v.notes]
    );
    res.status(201).json(toClient(rows[0]));
  } catch (error) {
    if (error instanceof Error && !error.code) return res.status(400).json({ error: error.message });
    next(error);
  }
});

app.put('/api/vehicles/:id', async (req, res, next) => {
  try {
    if (!/^[0-9a-f-]{36}$/i.test(req.params.id)) return res.status(400).json({ error: 'Identifiant véhicule invalide.' });
    const v = parseVehicle({ ...req.body, id: req.params.id }, req.params.id);
    const { rows } = await pool.query(
      `UPDATE vehicles SET make=$2, model=$3, year=$4, mileage=$5, buy_price=$6, other_costs=$7,
       resale_price=$8, status=$9, notes=$10, updated_at=NOW() WHERE id=$1 RETURNING ${selectColumns}`,
      [v.id, v.make, v.model, v.year, v.mileage, v.buyPrice, v.otherCosts, v.resalePrice, v.status, v.notes]
    );
    if (!rows.length) return res.status(404).json({ error: 'Véhicule introuvable.' });
    res.json(toClient(rows[0]));
  } catch (error) {
    if (error instanceof Error && !error.code) return res.status(400).json({ error: error.message });
    next(error);
  }
});

// One-time import keeps stock entered in the earlier browser-only version.
app.post('/api/vehicles/migrate', async (req, res, next) => {
  const records = req.body?.records;
  if (!Array.isArray(records) || records.length > 500) return res.status(400).json({ error: 'Import invalide.' });
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const count = await client.query('SELECT COUNT(*)::int AS count FROM vehicles');
    if (count.rows[0].count > 0) {
      await client.query('ROLLBACK');
      return res.status(409).json({ error: 'Le stock en ligne contient déjà des véhicules.' });
    }
    for (const record of records) {
      const v = parseVehicle(record);
      await client.query(
        `INSERT INTO vehicles (id, make, model, year, mileage, buy_price, other_costs, resale_price, status, notes)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) ON CONFLICT (id) DO NOTHING`,
        [v.id, v.make, v.model, v.year, v.mileage, v.buyPrice, v.otherCosts, v.resalePrice, v.status, v.notes]
      );
    }
    await client.query('COMMIT');
    const result = await client.query(`SELECT ${selectColumns} FROM vehicles ORDER BY updated_at DESC`);
    res.json(result.rows.map(toClient));
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    if (error instanceof Error && !error.code) return res.status(400).json({ error: error.message });
    next(error);
  } finally { client.release(); }
});

app.delete('/api/vehicles/:id', async (req, res, next) => {
  try {
    const { rowCount } = await pool.query('DELETE FROM vehicles WHERE id=$1', [req.params.id]);
    if (!rowCount) return res.status(404).json({ error: 'Véhicule introuvable.' });
    res.status(204).end();
  } catch (error) { next(error); }
});

app.use((error, _req, res, _next) => {
  console.error('Request failed:', error.message);
  res.status(500).json({ error: 'Erreur interne du serveur.' });
});

async function start() {
  if (pool) {
    await pool.query(`CREATE TABLE IF NOT EXISTS vehicles (
      id UUID PRIMARY KEY,
      make TEXT NOT NULL,
      model TEXT NOT NULL,
      year INTEGER,
      mileage INTEGER CHECK (mileage IS NULL OR mileage >= 0),
      buy_price NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (buy_price >= 0),
      other_costs NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (other_costs >= 0),
      resale_price NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (resale_price >= 0),
      status TEXT NOT NULL DEFAULT 'À préparer',
      notes TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )`);
  }
  app.listen(port, '0.0.0.0', () => console.log(`KP Cars listening on port ${port}`));
}

start().catch((error) => {
  console.error('KP Cars could not start:', error.message);
  process.exit(1);
});
