import React from 'react';
import {
  Brain, Briefcase, ChefHat, Cpu, Landmark, Lightbulb, Activity, Hash,
  Database, Book, Globe, Zap, Shield, Search, Code, MessageSquare, Layout,
  Layers, HardDrive, Cloud, Lock, User, Users, Target, Award, GraduationCap,
  Music, Video, Image, FileText, Mail, Terminal, Bug
} from 'lucide-react';

export const ICONS_LIST = [
  { name: 'Brain', icon: Brain },
  { name: 'Briefcase', icon: Briefcase },
  { name: 'ChefHat', icon: ChefHat },
  { name: 'Cpu', icon: Cpu },
  { name: 'Landmark', icon: Landmark },
  { name: 'Lightbulb', icon: Lightbulb },
  { name: 'Activity', icon: Activity },
  { name: 'Hash', icon: Hash },
  { name: 'Database', icon: Database },
  { name: 'Book', icon: Book },
  { name: 'Globe', icon: Globe },
  { name: 'Zap', icon: Zap },
  { name: 'Shield', icon: Shield },
  { name: 'Search', icon: Search },
  { name: 'Code', icon: Code },
  { name: 'MessageSquare', icon: MessageSquare },
  { name: 'Layout', icon: Layout },
  { name: 'Layers', icon: Layers },
  { name: 'HardDrive', icon: HardDrive },
  { name: 'Cloud', icon: Cloud },
  { name: 'Lock', icon: Lock },
  { name: 'User', icon: User },
  { name: 'Users', icon: Users },
  { name: 'Target', icon: Target },
  { name: 'Award', icon: Award },
  { name: 'GraduationCap', icon: GraduationCap },
  { name: 'Music', icon: Music },
  { name: 'Video', icon: Video },
  { name: 'Image', icon: Image },
  { name: 'FileText', icon: FileText },
  { name: 'Mail', icon: Mail },
  { name: 'Terminal', icon: Terminal },
  { name: 'Bug', icon: Bug },
];

interface SubjectIconProps {
  readonly iconName?: string;
  readonly className?: string;
  readonly size?: number;
}

export function SubjectIcon({ iconName, className, size }: SubjectIconProps) {
  const item = ICONS_LIST.find(i => i.name === iconName);
  const IconComponent = item ? item.icon : Hash;
  
  return <IconComponent className={className} size={size} />;
}
