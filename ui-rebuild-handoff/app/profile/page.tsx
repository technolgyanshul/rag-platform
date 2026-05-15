'use client';

import React, { useState } from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { User, Lock, Bell } from 'lucide-react';

export default function ProfilePage() {
  const [profile, setProfile] = useState({
    name: 'John Doe',
    email: 'john@example.com',
  });

  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState(profile);

  const handleSave = () => {
    setProfile(editForm);
    setIsEditing(false);
  };

  return (
    <DashboardLayout user={{ email: 'user@example.com', name: 'John Doe' }}>
      <PageHeader
        title="Profile & Settings"
        description="Manage your account settings and preferences"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        {/* Profile Section */}
        <div className="lg:col-span-2 space-y-4 md:space-y-6">
          {/* Account Information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User size={20} />
                Account Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!isEditing ? (
                <>
                  <div>
                    <label className="text-xs font-semibold text-muted-foreground">Name</label>
                    <p className="mt-1 text-foreground">{profile.name}</p>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-muted-foreground">Email</label>
                    <p className="mt-1 text-foreground">{profile.email}</p>
                  </div>
                  <Button onClick={() => setIsEditing(true)}>Edit Profile</Button>
                </>
              ) : (
                <>
                  <div>
                    <label className="text-xs font-semibold text-foreground block mb-2">Name</label>
                    <Input
                      value={editForm.name}
                      onChange={(e) =>
                        setEditForm({ ...editForm, name: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-foreground block mb-2">Email</label>
                    <Input
                      type="email"
                      value={editForm.email}
                      onChange={(e) =>
                        setEditForm({ ...editForm, email: e.target.value })
                      }
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleSave}>Save Changes</Button>
                    <Button variant="outline" onClick={() => {
                      setEditForm(profile);
                      setIsEditing(false);
                    }}>
                      Cancel
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Security */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lock size={20} />
                Security
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold text-foreground mb-2">Change Password</h4>
                <p className="text-xs text-muted-foreground mb-4">
                  Update your password to keep your account secure.
                </p>
                <Button variant="outline">Change Password</Button>
              </div>
              <div className="pt-4 border-t border-border">
                <h4 className="text-sm font-semibold text-foreground mb-2">API Keys</h4>
                <p className="text-xs text-muted-foreground mb-4">
                  Manage API keys for programmatic access to RAG Ops.
                </p>
                <Button variant="outline">Manage API Keys</Button>
              </div>
            </CardContent>
          </Card>

          {/* Notification Preferences */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell size={20} />
                Notifications
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Agent Status Updates</p>
                  <p className="text-xs text-muted-foreground">Get notified when agents go down</p>
                </div>
                <input type="checkbox" defaultChecked className="w-5 h-5" />
              </div>
              <div className="border-t border-border pt-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Query Failures</p>
                  <p className="text-xs text-muted-foreground">Get notified of failed queries</p>
                </div>
                <input type="checkbox" defaultChecked className="w-5 h-5" />
              </div>
              <div className="border-t border-border pt-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Knowledge Indexing</p>
                  <p className="text-xs text-muted-foreground">Get notified when indexing completes</p>
                </div>
                <input type="checkbox" defaultChecked className="w-5 h-5" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Account Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground">Account Type</p>
                <p className="text-sm font-medium text-foreground">Professional</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Member Since</p>
                <p className="text-sm font-medium text-foreground">January 2024</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Last Login</p>
                <p className="text-sm font-medium text-foreground">Today at 2:30 PM</p>
              </div>
              <Button variant="destructive" className="w-full mt-4">
                Delete Account
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Support</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start">
                Documentation
              </Button>
              <Button variant="outline" className="w-full justify-start">
                Contact Support
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
