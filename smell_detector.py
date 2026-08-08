
"""
Code Smell Detector
Implements detection rules from:
"An automatic code smell detection plugin using code metrics analysis"
"""
from typing import List, Dict
from java_parser import ClassInfo, MethodInfo


class SmellDetector:
    """Detects code smells based on metric thresholds."""

    def detect_smells(self, classes: List[ClassInfo]) -> List[ClassInfo]:
        """Run all smell detection rules on parsed classes."""
        for cls in classes:
            cls.smells = []

            # Class-level smells
            self._detect_god_class(cls)
            self._detect_data_class(cls)
            self._detect_brain_class(cls)
            self._detect_refused_parent_bequest(cls)
            self._detect_tradition_breaker(cls)

            # Method-level smells
            for method in cls.methods:
                self._detect_brain_method(cls, method)
                self._detect_feature_envy(cls, method)
                self._detect_intensive_coupling(cls, method)
                self._detect_dispersed_coupling(cls, method)
                self._detect_shotgun_surgery(cls, method)

        return classes

    def _detect_god_class(self, cls: ClassInfo):
        """God Class: ATFD > 3 && WMC >= 47 && TCC < 1/3"""
        # For class-level ATFD, sum method ATFDs
        class_atfd = sum(m.atfd for m in cls.methods)

        if class_atfd > 3 and cls.wmc >= 47 and cls.tcc < 1/3:
            cls.smells.append({
                'type': 'GodClass',
                'severity': 'High',
                'line': cls.start_line,
                'description': f"Class '{cls.name}' is a God Class. ATFD={class_atfd}, WMC={cls.wmc}, TCC={cls.tcc:.2f}",
                'metrics': {'ATFD': class_atfd, 'WMC': cls.wmc, 'TCC': round(cls.tcc, 2)}
            })

    def _detect_data_class(self, cls: ClassInfo):
        """Data Class: WOC < 1/3 && ((NOPA + NOAM > 3 && WMC < 31) || (NOPA + NOAM > 7 && WMC < 47))"""
        nopa_noam = cls.nopa + cls.noam

        if (cls.woc < 1/3 and 
            ((nopa_noam > 3 and cls.wmc < 31) or (nopa_noam > 7 and cls.wmc < 47))):
            cls.smells.append({
                'type': 'DataClass',
                'severity': 'Medium',
                'line': cls.start_line,
                'description': f"Class '{cls.name}' is a Data Class. WOC={cls.woc:.2f}, NOPA+NOAM={nopa_noam}, WMC={cls.wmc}",
                'metrics': {'WOC': round(cls.woc, 2), 'NOPA': cls.nopa, 'NOAM': cls.noam, 'WMC': cls.wmc}
            })

    def _detect_brain_class(self, cls: ClassInfo):
        """Brain Class: ((Brain Method > 1 && LOC >= 195) && (WMC >= 47 && TCC < 1/2)) || (Brain Method == 1 && LOC >= 390 && WMC >= 94)"""
        brain_methods = sum(1 for m in cls.methods if m.cyclo >= 4 and m.loc > 65)

        condition1 = (brain_methods > 1 and cls.loc >= 195 and cls.wmc >= 47 and cls.tcc < 1/2)
        condition2 = (brain_methods == 1 and cls.loc >= 390 and cls.wmc >= 94)

        if condition1 or condition2:
            cls.smells.append({
                'type': 'BrainClass',
                'severity': 'High',
                'line': cls.start_line,
                'description': f"Class '{cls.name}' is a Brain Class. BrainMethods={brain_methods}, LOC={cls.loc}, WMC={cls.wmc}",
                'metrics': {'BrainMethods': brain_methods, 'LOC': cls.loc, 'WMC': cls.wmc, 'TCC': round(cls.tcc, 2)}
            })

    def _detect_brain_method(self, cls: ClassInfo, method: MethodInfo):
        """Brain Method: LOC > 65 && CYCLO >= 4 && MAXNESTING >= 3 && NOAV > 7"""
        if (method.loc > 65 and method.cyclo >= 4 and 
            method.max_nesting >= 3 and method.noav > 7):
            cls.smells.append({
                'type': 'BrainMethod',
                'severity': 'High',
                'line': method.start_line,
                'description': f"Method '{method.name}' is a Brain Method. LOC={method.loc}, CYCLO={method.cyclo}, MAXNESTING={method.max_nesting}, NOAV={method.noav}",
                'metrics': {'LOC': method.loc, 'CYCLO': method.cyclo, 'MAXNESTING': method.max_nesting, 'NOAV': method.noav}
            })

    def _detect_feature_envy(self, cls: ClassInfo, method: MethodInfo):
        """Feature Envy: ATFD > 3 && LAA < 1/3 && FDP <= 3"""
        if method.atfd > 3 and method.laa < 1/3 and method.fdp <= 3:
            cls.smells.append({
                'type': 'FeatureEnvy',
                'severity': 'Medium',
                'line': method.start_line,
                'description': f"Method '{method.name}' has Feature Envy. ATFD={method.atfd}, LAA={method.laa:.2f}, FDP={method.fdp}",
                'metrics': {'ATFD': method.atfd, 'LAA': round(method.laa, 2), 'FDP': method.fdp}
            })

    def _detect_intensive_coupling(self, cls: ClassInfo, method: MethodInfo):
        """Intensive Coupling: (CINT > 7 && CDISP < 1/2) || ((CINT > 3) && (CDISP < 1/4) && (MAXNESTING > 1))"""
        condition1 = method.cint > 7 and method.cdisp < 1/2
        condition2 = method.cint > 3 and method.cdisp < 1/4 and method.max_nesting > 1

        if condition1 or condition2:
            cls.smells.append({
                'type': 'IntensiveCoupling',
                'severity': 'Medium',
                'line': method.start_line,
                'description': f"Method '{method.name}' has Intensive Coupling. CINT={method.cint}, CDISP={method.cdisp:.2f}, MAXNESTING={method.max_nesting}",
                'metrics': {'CINT': method.cint, 'CDISP': round(method.cdisp, 2), 'MAXNESTING': method.max_nesting}
            })

    def _detect_dispersed_coupling(self, cls: ClassInfo, method: MethodInfo):
        """Dispersed Coupling: (CINT > 7 && CDISP >= 1/2) && (MAXNESTING > 1)"""
        if method.cint > 7 and method.cdisp >= 1/2 and method.max_nesting > 1:
            cls.smells.append({
                'type': 'DispersedCoupling',
                'severity': 'Medium',
                'line': method.start_line,
                'description': f"Method '{method.name}' has Dispersed Coupling. CINT={method.cint}, CDISP={method.cdisp:.2f}, MAXNESTING={method.max_nesting}",
                'metrics': {'CINT': method.cint, 'CDISP': round(method.cdisp, 2), 'MAXNESTING': method.max_nesting}
            })

    def _detect_shotgun_surgery(self, cls: ClassInfo, method: MethodInfo):
        """Shotgun Surgery: CM > 7 && CC > 10"""
        if method.cm > 7 and method.cc > 10:
            cls.smells.append({
                'type': 'ShotgunSurgery',
                'severity': 'High',
                'line': method.start_line,
                'description': f"Method '{method.name}' indicates Shotgun Surgery. CM={method.cm}, CC={method.cc}",
                'metrics': {'CM': method.cm, 'CC': method.cc}
            })

    def _detect_refused_parent_bequest(self, cls: ClassInfo):
        """Refused Parent Bequest: ((NProtM > 3 && BUR < 1/3) || BOvR < 1/3) && ((AMW > 2 || WMC > 14) && NOM > 7)"""
        if not cls.parent_class:
            return

        condition1 = (cls.nprotm > 3 and cls.bur < 1/3) or cls.bovr < 1/3
        condition2 = (cls.amw > 2 or cls.wmc > 14) and cls.nom > 7

        if condition1 and condition2:
            cls.smells.append({
                'type': 'RefusedParentBequest',
                'severity': 'Medium',
                'line': cls.start_line,
                'description': f"Class '{cls.name}' shows Refused Parent Bequest. NProtM={cls.nprotm}, BUR={cls.bur:.2f}, BOvR={cls.bovr:.2f}",
                'metrics': {'NProtM': cls.nprotm, 'BUR': round(cls.bur, 2), 'BOvR': round(cls.bovr, 2), 'AMW': round(cls.amw, 2), 'WMC': cls.wmc, 'NOM': cls.nom}
            })

    def _detect_tradition_breaker(self, cls: ClassInfo):
        """Tradition Breaker: (NAS >= 7 && PNAS >= 2/3) && ((AMW > 2 || WMC >= 47) && NOM >= 10) && (AMW > 2 && NOM > 5 && WMC >= 24)"""
        if not cls.parent_class:
            return

        condition1 = cls.nas >= 7 and cls.pnas >= 2/3
        condition2 = (cls.amw > 2 or cls.wmc >= 47) and cls.nom >= 10
        condition3 = cls.amw > 2 and cls.nom > 5 and cls.wmc >= 24

        if condition1 and condition2 and condition3:
            cls.smells.append({
                'type': 'TraditionBreaker',
                'severity': 'Medium',
                'line': cls.start_line,
                'description': f"Class '{cls.name}' is a Tradition Breaker. NAS={cls.nas}, PNAS={cls.pnas:.2f}",
                'metrics': {'NAS': cls.nas, 'PNAS': round(cls.pnas, 2), 'AMW': round(cls.amw, 2), 'NOM': cls.nom, 'WMC': cls.wmc}
            })
