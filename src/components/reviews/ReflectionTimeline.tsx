import React, { useState } from 'react';
import { toast } from 'sonner';
import { Lightbulb, ShieldAlert, MessageSquare, Trash2, Calendar, Star, Clock, Plus, HelpCircle, Heart, MessageCircle, Link2 } from 'lucide-react';
import { ReviewEntryResponse } from '@/services/api/types';
import { ReflectionForm } from './ReflectionForm';

interface ReflectionTimelineProps {
  reflections: ReviewEntryResponse[];
  onAddReflection: (payload: {
    tradeDate: string;
    actionType: string;
    disciplineScore: number;
    emotionTags: string[];
    problemTags: string[];
    reasonText: string;
    reflectionText: string;
    conclusionText: string;
    nextActionText: string;
    outcomeText?: string | null;
  }) => Promise<void>;
  onDeleteReflection: (id: string) => Promise<void>;
  onUpdateReflection: (id: string, payload: any) => Promise<void>;
}

// Simple custom inline markdown parser for bold, italics, and line-breaks
const renderMarkdown = (text: string) => {
  if (!text) return null;
  
  const lines = text.split('\n');
  return lines.map((line, idx) => {
    // Check if it's a bullet point
    const isBullet = line.trim().startsWith('-') || line.trim().startsWith('*');
    const content = isBullet ? line.replace(/^[\s-*]+/, '') : line;
    
    // Parse bold markdown (**text**)
    const boldRegex = /\*\*([^*]+)\*\*/g;
    const parts = [];
    let lastIndex = 0;
    let match;
    
    while ((match = boldRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }
      parts.push(<strong key={match.index} className="font-bold text-slate-900">{match[1]}</strong>);
      lastIndex = boldRegex.lastIndex;
    }
    
    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    if (isBullet) {
      return (
        <li key={idx} className="ml-4 list-disc pl-1 mt-1 text-slate-700">
          {parts.length > 0 ? parts : content}
        </li>
      );
    }

    return (
      <p key={idx} className="min-h-[1rem] leading-relaxed mt-1 text-slate-700 text-[13px] tracking-wide">
        {parts.length > 0 ? parts : content}
      </p>
    );
  });
};

export const ReflectionTimeline = ({
  reflections,
  onAddReflection,
  onDeleteReflection,
  onUpdateReflection,
}: ReflectionTimelineProps) => {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Likes persistent state (using LocalStorage to avoid backend db changes)
  const [likedPosts, setLikedPosts] = useState<string[]>(() => {
    const saved = localStorage.getItem('waytofree_dojo_liked_posts');
    return saved ? JSON.parse(saved) : [];
  });

  // Comments interactive states
  const [activeCommentsPostId, setActiveCommentsPostId] = useState<string | null>(null);
  const [commentText, setCommentText] = useState('');

  const handleAddSubmit = async (payload: any) => {
    await onAddReflection(payload);
    setIsFormOpen(false);
  };

  // Helper to determine category badges
  const getCategoryDetails = (actionType: string) => {
    switch (actionType) {
      case '心法顿悟':
        return {
          icon: Lightbulb,
          color: 'text-amber-500 bg-amber-50 border-amber-100',
          title: '💡 心法顿悟',
        };
      case '盘后忏悔':
        return {
          icon: ShieldAlert,
          color: 'text-rose-500 bg-rose-50 border-rose-100',
          title: '⚠️ 盘后忏悔',
        };
      case '自我对话':
        return {
          icon: MessageSquare,
          color: 'text-indigo-500 bg-indigo-50 border-indigo-100',
          title: '💬 自我对话',
        };
      default:
        return {
          icon: Lightbulb,
          color: 'text-blue-500 bg-blue-50 border-blue-100',
          title: '📝 随笔感触',
        };
    }
  };

  // Likes toggle handler
  const handleToggleLike = (id: string) => {
    let nextLiked: string[];
    if (likedPosts.includes(id)) {
      nextLiked = likedPosts.filter((x) => x !== id);
      toast.success('已取消点赞');
    } else {
      nextLiked = [...likedPosts, id];
      toast.success('给你自己的深刻反思点了个赞！👍');
    }
    setLikedPosts(nextLiked);
    localStorage.setItem('waytofree_dojo_liked_posts', JSON.stringify(nextLiked));
  };

  // Parse comments list stored as JSON string in reflectionText field
  const parseComments = (reflectionText: string | null): Array<{ id: string; text: string; time: string }> => {
    if (!reflectionText || reflectionText === '-') return [];
    try {
      const parsed = JSON.parse(reflectionText);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  };

  // Add a new comment (persisted to SQLite db)
  const handleAddComment = async (ref: ReviewEntryResponse) => {
    if (!commentText.trim()) return;

    const comments = parseComments(ref.reflectionText);
    const newComment = {
      id: `cmt-${Date.now()}`,
      text: commentText.trim(),
      time: new Date().toISOString().slice(5, 10) + ' ' + new Date().toTimeString().slice(0, 5), // "MM-DD HH:MM"
    };

    const updatedComments = [...comments, newComment];
    try {
      await onUpdateReflection(ref.id, { reflectionText: JSON.stringify(updatedComments) });
      setCommentText('');
      toast.success('感悟追加成功！');
    } catch (err) {
      toast.error('发表评论失败');
    }
  };

  // Delete a comment (persisted to SQLite db)
  const handleDeleteComment = async (ref: ReviewEntryResponse, commentId: string) => {
    const comments = parseComments(ref.reflectionText);
    const updatedComments = comments.filter((c) => c.id !== commentId);

    try {
      await onUpdateReflection(ref.id, {
        reflectionText: updatedComments.length > 0 ? JSON.stringify(updatedComments) : '-',
      });
      toast.success('追加感悟已撤回');
    } catch (err) {
      toast.error('删除评论失败');
    }
  };

  return (
    <div className="space-y-4">
      {/* Action Row */}
      {!isFormOpen && (
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="h-4 w-4" />
            交易心路日记说说 ({reflections.length})
          </h3>
          <button
            onClick={() => setIsFormOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-md bg-blue-600 px-4 text-xs font-bold text-white shadow-xs hover:bg-blue-700 transition-colors animate-in fade-in"
          >
            <Plus className="h-4 w-4" />
            写新说说
          </button>
        </div>
      )}

      {/* Form Container */}
      {isFormOpen && (
        <ReflectionForm
          onSubmit={handleAddSubmit}
          onCancel={() => setIsFormOpen(false)}
        />
      )}

      {/* Vertical Moments Feed */}
      <div className="relative border-l border-slate-200 ml-4.5 pl-6 space-y-6">
        {reflections.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center">
            <HelpCircle className="mx-auto h-10 w-10 text-slate-300" />
            <h4 className="mt-3 text-xs font-bold text-slate-800">暂无日记说说记录</h4>
            <p className="mt-1 text-[11px] text-slate-500 max-w-sm mx-auto">
              有什么想吐槽的心态、或者闪现的灵光？点击上方“写新说说”，发条属于你自己的日记说说吧。
            </p>
          </div>
        ) : (
          reflections.map((ref) => {
            const actionType = ref.sectorTags[0] || '心法顿悟';
            const cat = getCategoryDetails(actionType);
            const isDeleting = confirmDeleteId === ref.id;
            const commentsList = parseComments(ref.reflectionText);

            return (
              <div key={ref.id} className="relative group">
                {/* Timeline Bullet Dot */}
                <div className={`absolute -left-[35px] top-4.5 flex h-7 w-7 items-center justify-center rounded-full border ring-8 ring-slate-100/50 ${cat.color}`}>
                  <cat.icon className="h-3.5 w-3.5" />
                </div>

                {/* Moments Post Card */}
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition-all duration-200 hover:shadow-md hover:border-slate-300">
                  {/* Moments User Profile Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      {/* Avatar Wrapper */}
                      <div className="h-10 w-10 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-xs text-slate-500 uppercase">
                        {actionType.slice(2, 3) || '修'}
                      </div>
                      <div>
                        {/* Nickname & Category tag */}
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-800">交易修行者</span>
                          <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[9px] font-bold border ${cat.color}`}>
                            {cat.title}
                          </span>
                        </div>
                        {/* Publish date */}
                        <div className="text-[10px] text-slate-400 font-medium mt-0.5 flex items-center gap-1">
                          <Calendar className="h-3 w-3 text-slate-300" />
                          发表于 {ref.tradeDate}
                        </div>
                      </div>
                    </div>

                    {/* Delete trigger */}
                    <div className="flex items-center gap-2.5">
                      {isDeleting ? (
                        <div className="flex items-center gap-1.5 bg-rose-50 border border-rose-200 rounded px-2 py-0.5 animate-in slide-in-from-right-2 duration-150">
                          <span className="text-[9px] font-bold text-rose-700">删除？</span>
                          <button
                            onClick={() => onDeleteReflection(ref.id)}
                            className="text-[9px] font-bold text-rose-600 hover:text-rose-800"
                          >
                            是
                          </button>
                          <span className="text-rose-300 text-[9px]">|</span>
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            className="text-[9px] font-bold text-slate-600 hover:text-slate-800"
                          >
                            否
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmDeleteId(ref.id)}
                          className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 transition-all p-1"
                          title="删除记录"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Moments musings body text */}
                  <div className="mt-3.5 pl-0.5 pr-1 text-slate-800 font-sans tracking-wide whitespace-pre-line leading-relaxed text-[13px]">
                    {renderMarkdown(ref.conclusionText)}
                  </div>

                  {/* External Reference Shared Link Card */}
                  {ref.outcomeText && (
                    <div className="mt-3 select-all animate-in fade-in duration-200">
                      <a
                        href={ref.outcomeText.startsWith('http') ? ref.outcomeText : `https://${ref.outcomeText}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-3 w-full rounded-lg bg-slate-50 border border-slate-200/60 p-2.5 hover:bg-slate-100/70 hover:border-slate-300 transition-all group"
                      >
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-blue-50 text-blue-600 border border-blue-100">
                          <Link2 className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-[11px] font-bold text-slate-800 truncate group-hover:text-blue-600 transition-colors">
                            查看参考链接 / 外部灵感来源
                          </div>
                          <div className="text-[10px] text-slate-400 truncate mt-0.5 font-mono">
                            {ref.outcomeText}
                          </div>
                        </div>
                      </a>
                    </div>
                  )}

                  {/* Moments Hashtags section */}
                  <div className="mt-3.5 flex flex-wrap gap-x-2.5 gap-y-1.5 border-t border-slate-50 pt-3">
                    {ref.emotionTags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs font-semibold text-blue-600 hover:underline cursor-pointer"
                      >
                        #{tag}
                      </span>
                    ))}
                    {ref.problemTags.map((tag) => (
                      <span
                        key={tag}
                        className={`text-xs font-semibold hover:underline cursor-pointer ${
                          tag === '自我管理' ? 'text-slate-500' : 'text-rose-600'
                        }`}
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>

                  {/* Moments Post Action Footer */}
                  <div className="mt-4 flex items-center justify-between border-t border-slate-100/70 pt-3.5 text-[10px] text-slate-400">
                    <div className="flex items-center gap-1">
                      <span className="font-semibold text-slate-500">自律定力自评：</span>
                      <div className="flex items-center gap-0.5">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <Star
                            key={star}
                            className={`h-3.5 w-3.5 ${
                              star <= ref.disciplineScore
                                ? 'fill-amber-400 text-amber-400'
                                : 'text-slate-200'
                            }`}
                          />
                        ))}
                      </div>
                    </div>

                    {/* Interactive Likes & Comments Buttons */}
                    <div className="flex items-center gap-4 select-none">
                      {/* Like Button */}
                      <button
                        onClick={() => handleToggleLike(ref.id)}
                        className={`flex items-center gap-1 hover:text-rose-600 transition-colors font-semibold ${
                          likedPosts.includes(ref.id) ? 'text-rose-500' : 'text-slate-400'
                        }`}
                      >
                        <Heart className={`h-3.5 w-3.5 ${likedPosts.includes(ref.id) ? 'fill-rose-500 text-rose-500' : ''}`} />
                        {likedPosts.includes(ref.id) ? '已赞' : '赞'}
                      </button>

                      {/* Comment Button */}
                      <button
                        onClick={() => {
                          if (activeCommentsPostId === ref.id) {
                            setActiveCommentsPostId(null);
                          } else {
                            setActiveCommentsPostId(ref.id);
                            setCommentText('');
                          }
                        }}
                        className={`flex items-center gap-1 hover:text-blue-600 transition-colors font-semibold ${
                          activeCommentsPostId === ref.id ? 'text-blue-500' : 'text-slate-400'
                        }`}
                      >
                        <MessageCircle className="h-3.5 w-3.5" />
                        评论 {commentsList.length > 0 ? `(${commentsList.length})` : ''}
                      </button>
                    </div>
                  </div>

                  {/* WeChat Moments Style Comments Board */}
                  {(commentsList.length > 0 || activeCommentsPostId === ref.id) && (
                    <div className="mt-3.5 rounded-lg bg-slate-50 border border-slate-100 p-3 space-y-2.5 animate-in slide-in-from-top-2 duration-150">
                      
                      {/* Historical Comments List */}
                      {commentsList.length > 0 && (
                        <div className="space-y-2 max-h-48 overflow-y-auto pr-1 border-b border-slate-200/40 pb-2.5">
                          {commentsList.map((cmt) => (
                            <div key={cmt.id} className="group/cmt flex items-start justify-between gap-3 text-xs leading-relaxed">
                              <div className="min-w-0 flex-1">
                                <span className="font-bold text-blue-600 mr-1.5">我 (追加):</span>
                                <span className="text-slate-700 font-sans tracking-wide">{cmt.text}</span>
                              </div>
                              <div className="flex items-center gap-2 shrink-0 select-none text-[10px] text-slate-400">
                                <span className="font-mono text-[9px]">{cmt.time}</span>
                                {/* Hover Delete comment */}
                                <button
                                  onClick={() => handleDeleteComment(ref, cmt.id)}
                                  className="opacity-0 group-hover/cmt:opacity-100 text-slate-400 hover:text-rose-600 p-0.5 rounded transition-all"
                                  title="撤回该感悟"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Inline Comment Input Box */}
                      {activeCommentsPostId === ref.id && (
                        <div className="flex items-center gap-2 pt-1" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="text"
                            required
                            value={commentText}
                            onChange={(e) => setCommentText(e.target.value)}
                            placeholder="追加日盘后感受、第二天的交易验证..."
                            className="flex-1 h-8 rounded border border-slate-200 bg-white px-2.5 text-xs outline-none focus:ring-2 focus:ring-blue-100 font-sans"
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleAddComment(ref);
                            }}
                          />
                          <button
                            onClick={() => handleAddComment(ref)}
                            className="h-8 rounded bg-blue-600 px-3.5 text-xs font-bold text-white hover:bg-blue-700 transition-colors"
                          >
                            发送
                          </button>
                        </div>
                      )}

                    </div>
                  )}

                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
