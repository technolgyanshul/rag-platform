"use client";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AppShell } from "../../components/layout/AppShell";

const members = [
  { name: "Marcus Chen", role: "Admin", email: "m.chen@sentientops.ai", status: "Active" },
  { name: "Sarah Jenkins", role: "Operator", email: "s.jenkins@sentientops.ai", status: "Active" },
  { name: "David Torres", role: "Viewer", email: "d.torres@sentientops.ai", status: "Inactive" },
  { name: "Alain Dubois", role: "Operator", email: "a.dubois@sentientops.ai", status: "Active" },
];

export default function TeamPage() {
  return (
    <ProtectedPage>
      <AppShell
        title="Team Management"
        subtitle="Manage operators, permissions, and collaboration groups"
        actions={<button type="button">Invite Member</button>}
      >
        <div className="split-3">
          <article className="metric-card">
            <h3>Total Members</h3>
            <p>24</p>
          </article>
          <article className="metric-card">
            <h3>Active Teams</h3>
            <p>6</p>
          </article>
          <article className="metric-card">
            <h3>Pending Invites</h3>
            <p>3</p>
          </article>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Members</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.email}>
                    <td>{member.name}</td>
                    <td>{member.email}</td>
                    <td>{member.role}</td>
                    <td>
                      <span className={`badge ${member.status === "Active" ? "badge--success" : "badge--warn"}`}>
                        {member.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
