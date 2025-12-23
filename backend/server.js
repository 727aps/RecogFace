const express = require('express');
const cors = require('cors');
const path = require('path');
const Database = require('better-sqlite3');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, '../frontend/dist')));

// Optional SQLite database for persistence
let db;
try {
    db = new Database('./faceidhub.db');
    // Create tables
    db.exec(`
        CREATE TABLE IF NOT EXISTS persons (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            encoding_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            person_id TEXT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES persons(id)
        );
    `);
    console.log('Database initialized');
} catch (err) {
    console.log('Database not available, running in-memory mode');
}

// Routes
app.post('/api/enroll', (req, res) => {
    try {
        const { name, encodingHash } = req.body;

        if (!name || !encodingHash) {
            return res.status(400).json({ error: 'Name and encoding hash required' });
        }

        const personId = uuidv4();

        if (db) {
            const stmt = db.prepare('INSERT INTO persons (id, name, encoding_hash) VALUES (?, ?, ?)');
            stmt.run(personId, name, encodingHash);

            // Log enrollment
            const logStmt = db.prepare('INSERT INTO sessions (id, person_id, action) VALUES (?, ?, ?)');
            logStmt.run(uuidv4(), personId, 'enroll');
        }

        res.json({
            success: true,
            personId,
            message: 'Person enrolled successfully'
        });
    } catch (error) {
        console.error('Enrollment error:', error);
        res.status(500).json({ error: 'Enrollment failed' });
    }
});

app.get('/api/persons', (req, res) => {
    try {
        if (!db) {
            return res.json({ persons: [] });
        }

        const stmt = db.prepare('SELECT id, name, created_at FROM persons ORDER BY created_at DESC');
        const persons = stmt.all();

        res.json({ persons });
    } catch (error) {
        console.error('Get persons error:', error);
        res.status(500).json({ error: 'Failed to retrieve persons' });
    }
});

app.delete('/api/persons/:id', (req, res) => {
    try {
        const { id } = req.params;

        if (!db) {
            return res.json({ success: true });
        }

        // Delete person
        const deleteStmt = db.prepare('DELETE FROM persons WHERE id = ?');
        const result = deleteStmt.run(id);

        if (result.changes > 0) {
            // Log deletion
            const logStmt = db.prepare('INSERT INTO sessions (id, person_id, action) VALUES (?, ?, ?)');
            logStmt.run(uuidv4(), id, 'delete');

            res.json({ success: true });
        } else {
            res.status(404).json({ error: 'Person not found' });
        }
    } catch (error) {
        console.error('Delete person error:', error);
        res.status(500).json({ error: 'Failed to delete person' });
    }
});

app.get('/api/logs', (req, res) => {
    try {
        if (!db) {
            return res.json({ logs: [] });
        }

        const stmt = db.prepare(`
            SELECT s.timestamp, s.action, p.name
            FROM sessions s
            LEFT JOIN persons p ON s.person_id = p.id
            ORDER BY s.timestamp DESC
            LIMIT 100
        `);
        const logs = stmt.all();

        res.json({ logs });
    } catch (error) {
        console.error('Get logs error:', error);
        res.status(500).json({ error: 'Failed to retrieve logs' });
    }
});

app.post('/api/logs', (req, res) => {
    try {
        const { action, personName } = req.body;

        if (!db) {
            return res.json({ success: true });
        }

        // Find person ID by name (simplified)
        let personId = null;
        if (personName && personName !== 'Unknown') {
            const stmt = db.prepare('SELECT id FROM persons WHERE name = ?');
            const person = stmt.get(personName);
            personId = person ? person.id : null;
        }

        const logStmt = db.prepare('INSERT INTO sessions (id, person_id, action) VALUES (?, ?, ?)');
        logStmt.run(uuidv4(), personId, action);

        res.json({ success: true });
    } catch (error) {
        console.error('Log error:', error);
        res.status(500).json({ error: 'Failed to log event' });
    }
});

app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        database: db ? 'connected' : 'disabled'
    });
});

// Serve React app for all other routes
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/dist/index.html'));
});

app.listen(PORT, () => {
    console.log(`FaceIDHub server running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/health`);
});
