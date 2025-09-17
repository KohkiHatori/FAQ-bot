"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { highlightText, searchFAQs } from "@/lib/highlight";
import { AlertCircle, ArrowLeft, CheckCircle, Edit, Plus, RefreshCw, Search, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const API_BASE_URL = "http://localhost:8000";

interface FAQ {
  id: number;
  question: string;
  answer: string;
  created_at?: string;
  updated_at?: string;
}

interface FAQListResponse {
  faqs: FAQ[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

type NotificationType = "success" | "error" | "info";

interface Notification {
  id: string;
  type: NotificationType;
  message: string;
}

export default function AdminPage() {
  const [allFaqs, setAllFaqs] = useState<FAQ[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(0);
  const [totalFAQs, setTotalFAQs] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isSearchingAll, setIsSearchingAll] = useState(false);
  const [allFaqsLoaded, setAllFaqsLoaded] = useState(false);

  // Dialog states
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedFAQ, setSelectedFAQ] = useState<FAQ | null>(null);

  // Form states
  const [formData, setFormData] = useState({ question: "", answer: "" });
  const [formLoading, setFormLoading] = useState(false);

  const ITEMS_PER_PAGE = 20;

  // Debounced search - updates debouncedSearchQuery after 300ms delay
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Client-side filtered FAQs based on debounced search query
  const filteredFaqs = useMemo(() => {
    return searchFAQs(allFaqs, debouncedSearchQuery);
  }, [allFaqs, debouncedSearchQuery]);

  // Notification system
  const addNotification = (type: NotificationType, message: string) => {
    const id = Math.random().toString(36).substr(2, 9);
    const notification = { id, type, message };
    setNotifications(prev => [...prev, notification]);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  // API functions
  const fetchFAQs = async (page = 0, append = false) => {
    setLoading(true);
    try {
      const offset = page * ITEMS_PER_PAGE;
      const response = await fetch(`${API_BASE_URL}/faqs?limit=${ITEMS_PER_PAGE}&offset=${offset}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch FAQs: ${response.statusText}`);
      }

      const data: FAQListResponse = await response.json();

      if (append) {
        setAllFaqs(prev => [...prev, ...data.faqs]);
      } else {
        setAllFaqs(data.faqs);
      }

      setTotalFAQs(data.total);
      setHasMore(data.has_more);
      setCurrentPage(page);
    } catch (error) {
      console.error("Error fetching FAQs:", error);
      addNotification("error", `Failed to fetch FAQs: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  };

  const loadAllFAQs = async () => {
    if (allFaqsLoaded) {
      addNotification("info", "All FAQs are already loaded");
      return;
    }

    setIsSearchingAll(true);
    try {
      // Fetch all FAQs with a large limit
      const response = await fetch(`${API_BASE_URL}/faqs?limit=${totalFAQs || 10000}&offset=0`);

      if (!response.ok) {
        throw new Error(`Failed to fetch all FAQs: ${response.statusText}`);
      }

      const data: FAQListResponse = await response.json();

      setAllFaqs(data.faqs);
      setTotalFAQs(data.total);
      setHasMore(false);
      setAllFaqsLoaded(true);

      addNotification("success", `Loaded all ${data.faqs.length} FAQs for comprehensive search`);
    } catch (error) {
      console.error("Error loading all FAQs:", error);
      addNotification("error", `Failed to load all FAQs: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsSearchingAll(false);
    }
  };

  const createFAQ = async (question: string, answer: string) => {
    setFormLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/faqs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, answer }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to create FAQ: ${response.statusText}`);
      }

      const data = await response.json();
      addNotification("success", `FAQ created successfully with ID: ${data.faq.id}`);

      // Refresh the list
      fetchFAQs(0);
      setAllFaqsLoaded(false); // Reset so user can load all FAQs again after changes

      setIsCreateDialogOpen(false);
      setFormData({ question: "", answer: "" });
    } catch (error) {
      console.error("Error creating FAQ:", error);
      addNotification("error", `Failed to create FAQ: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setFormLoading(false);
    }
  };

  const updateFAQ = async (id: number, question?: string, answer?: string) => {
    setFormLoading(true);
    try {
      const updateData: any = {};
      if (question !== undefined) updateData.question = question;
      if (answer !== undefined) updateData.answer = answer;

      const response = await fetch(`${API_BASE_URL}/faqs/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(updateData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to update FAQ: ${response.statusText}`);
      }

      const data = await response.json();
      addNotification("success", `FAQ ${id} updated successfully`);

      // Refresh the list
      fetchFAQs(currentPage);
      setAllFaqsLoaded(false); // Reset so user can load all FAQs again after changes

      setIsEditDialogOpen(false);
      setSelectedFAQ(null);
      setFormData({ question: "", answer: "" });
    } catch (error) {
      console.error("Error updating FAQ:", error);
      addNotification("error", `Failed to update FAQ: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setFormLoading(false);
    }
  };

  const deleteFAQ = async (id: number) => {
    setFormLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/faqs/${id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to delete FAQ: ${response.statusText}`);
      }

      addNotification("success", `FAQ ${id} deleted successfully`);

      // Refresh the list
      fetchFAQs(currentPage);
      setAllFaqsLoaded(false); // Reset so user can load all FAQs again after changes

      setIsDeleteDialogOpen(false);
      setSelectedFAQ(null);
    } catch (error) {
      console.error("Error deleting FAQ:", error);
      addNotification("error", `Failed to delete FAQ: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setFormLoading(false);
    }
  };

  // Event handlers
  const handleLoadMore = () => {
    if (!loading && hasMore) {
      fetchFAQs(currentPage + 1, true);
    }
  };

  const handleEditClick = (faq: FAQ) => {
    setSelectedFAQ(faq);
    setFormData({ question: faq.question, answer: faq.answer });
    setIsEditDialogOpen(true);
  };

  const handleDeleteClick = (faq: FAQ) => {
    setSelectedFAQ(faq);
    setIsDeleteDialogOpen(true);
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.question.trim() && formData.answer.trim()) {
      createFAQ(formData.question, formData.answer);
    }
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFAQ && formData.question.trim() && formData.answer.trim()) {
      updateFAQ(selectedFAQ.id, formData.question, formData.answer);
    }
  };

  // Initial load
  useEffect(() => {
    fetchFAQs(0);
  }, []);

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-4">
          <Link href="/">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Chat
            </Button>
          </Link>
        </div>
        <h1 className="text-3xl font-bold mb-2">FAQ Management</h1>
        <p className="text-muted-foreground">
          Manage your FAQ database with full CRUD operations
        </p>
      </div>

      {/* Notifications */}
      {notifications.length > 0 && (
        <div className="fixed top-4 right-4 z-50 space-y-2">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className={`flex items-center gap-2 p-4 rounded-lg shadow-lg border max-w-md ${notification.type === "success"
                ? "bg-green-50 border-green-200 text-green-800"
                : notification.type === "error"
                  ? "bg-red-50 border-red-200 text-red-800"
                  : "bg-blue-50 border-blue-200 text-blue-800"
                }`}
            >
              {notification.type === "success" && <CheckCircle className="h-4 w-4" />}
              {notification.type === "error" && <AlertCircle className="h-4 w-4" />}
              {notification.type === "info" && <AlertCircle className="h-4 w-4" />}
              <span className="text-sm">{notification.message}</span>
              <button
                onClick={() => removeNotification(notification.id)}
                className="ml-auto text-current hover:opacity-70"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Controls */}
      <div className="mb-6 space-y-4">
        {/* Search Bar */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search FAQs (real-time)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button
            variant="outline"
            onClick={loadAllFAQs}
            disabled={isSearchingAll || allFaqsLoaded}
            className="whitespace-nowrap"
          >
            {isSearchingAll ? (
              <RefreshCw className="h-4 w-4 animate-spin mr-2" />
            ) : allFaqsLoaded ? (
              <CheckCircle className="h-4 w-4 mr-2" />
            ) : (
              <Search className="h-4 w-4 mr-2" />
            )}
            {allFaqsLoaded ? "All Loaded" : "Search All"}
          </Button>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Badge variant="outline">
              {debouncedSearchQuery ? `${filteredFaqs.length} of ${totalFAQs} FAQs` : `${totalFAQs} total FAQs`}
            </Badge>
            {allFaqsLoaded && (
              <Badge variant="default">
                All {allFaqs.length} FAQs loaded
              </Badge>
            )}
            {debouncedSearchQuery && (
              <Badge variant="secondary">
                Searching: "{debouncedSearchQuery}"
              </Badge>
            )}
            {searchQuery !== debouncedSearchQuery && searchQuery && (
              <Badge variant="outline" className="animate-pulse">
                Typing...
              </Badge>
            )}
          </div>

          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add FAQ
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Create New FAQ</DialogTitle>
                <DialogDescription>
                  Add a new frequently asked question and its answer.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateSubmit}>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Question</label>
                    <Input
                      placeholder="Enter the question..."
                      value={formData.question}
                      onChange={(e) => setFormData(prev => ({ ...prev, question: e.target.value }))}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">Answer</label>
                    <Textarea
                      placeholder="Enter the answer..."
                      value={formData.answer}
                      onChange={(e) => setFormData(prev => ({ ...prev, answer: e.target.value }))}
                      rows={6}
                      required
                    />
                  </div>
                </div>
                <DialogFooter className="mt-6">
                  <Button type="button" variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={formLoading}>
                    {formLoading ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : null}
                    Create FAQ
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* FAQ List */}
      <div className="space-y-4">
        {loading && allFaqs.length === 0 ? (
          <div className="flex justify-center items-center py-12">
            <RefreshCw className="h-6 w-6 animate-spin mr-2" />
            <span>Loading FAQs...</span>
          </div>
        ) : filteredFaqs.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">
              {debouncedSearchQuery ? `No FAQs found matching "${debouncedSearchQuery}"` : "No FAQs found."}
            </p>
          </div>
        ) : (
          <>
            {filteredFaqs.map((faq) => (
              <Card key={faq.id} className="relative">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <CardTitle className="text-lg mb-2">
                        <span className="text-muted-foreground text-sm font-normal mr-2">
                          ID: {faq.id}
                        </span>
                        <span
                          dangerouslySetInnerHTML={{
                            __html: highlightText(faq.question, debouncedSearchQuery)
                          }}
                        />
                      </CardTitle>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEditClick(faq)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteClick(faq)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p
                    className="text-sm leading-relaxed whitespace-pre-wrap"
                    dangerouslySetInnerHTML={{
                      __html: highlightText(faq.answer, debouncedSearchQuery)
                    }}
                  />
                </CardContent>
                <CardFooter className="text-xs text-muted-foreground">
                  <div className="flex justify-between w-full">
                    <span>Created: {formatDate(faq.created_at)}</span>
                    {faq.updated_at && faq.updated_at !== faq.created_at && (
                      <span>Updated: {formatDate(faq.updated_at)}</span>
                    )}
                  </div>
                </CardFooter>
              </Card>
            ))}

            {/* Load More Button - only show when not searching and not all loaded */}
            {hasMore && !debouncedSearchQuery && !allFaqsLoaded && (
              <div className="flex justify-center py-6">
                <Button
                  variant="outline"
                  onClick={handleLoadMore}
                  disabled={loading}
                >
                  {loading ? (
                    <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                  ) : null}
                  Load More ({totalFAQs - allFaqs.length} remaining)
                </Button>
              </div>
            )}

            {/* Show message when searching but more FAQs available */}
            {debouncedSearchQuery && !allFaqsLoaded && hasMore && (
              <div className="text-center py-4 text-sm text-muted-foreground border-t">
                Searching {allFaqs.length} of {totalFAQs} FAQs.
                <Button
                  variant="link"
                  size="sm"
                  onClick={loadAllFAQs}
                  disabled={isSearchingAll}
                  className="ml-1"
                >
                  {isSearchingAll ? "Loading..." : "Load all FAQs for complete search"}
                </Button>
              </div>
            )}

            {/* Show message when all FAQs are loaded */}
            {allFaqsLoaded && !debouncedSearchQuery && (
              <div className="text-center py-4 text-sm text-muted-foreground border-t">
                All {allFaqs.length} FAQs loaded - search will cover the entire database
              </div>
            )}
          </>
        )}
      </div>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit FAQ #{selectedFAQ?.id}</DialogTitle>
            <DialogDescription>
              Update the question and answer for this FAQ.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleEditSubmit}>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Question</label>
                <Input
                  placeholder="Enter the question..."
                  value={formData.question}
                  onChange={(e) => setFormData(prev => ({ ...prev, question: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Answer</label>
                <Textarea
                  placeholder="Enter the answer..."
                  value={formData.answer}
                  onChange={(e) => setFormData(prev => ({ ...prev, answer: e.target.value }))}
                  rows={6}
                  required
                />
              </div>
            </div>
            <DialogFooter className="mt-6">
              <Button type="button" variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={formLoading}>
                {formLoading ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : null}
                Update FAQ
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete FAQ #{selectedFAQ?.id}</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this FAQ? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {selectedFAQ && (
            <div className="my-4 p-4 bg-muted rounded-lg">
              <p className="font-medium mb-2">{selectedFAQ.question}</p>
              <p className="text-sm text-muted-foreground line-clamp-3">
                {selectedFAQ.answer}
              </p>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => selectedFAQ && deleteFAQ(selectedFAQ.id)}
              disabled={formLoading}
            >
              {formLoading ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : null}
              Delete FAQ
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
